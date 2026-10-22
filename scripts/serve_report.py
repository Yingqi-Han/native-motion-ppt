#!/usr/bin/env python3
"""Serve an offline delivery locally, including byte ranges for video seeking."""
import argparse
import functools
import http.server
import re
from pathlib import Path
from urllib.parse import quote


class ReportHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

    def send_head(self):
        self.byte_range=None
        path=Path(self.translate_path(self.path))
        header=self.headers.get("Range")
        if not header or not path.is_file():return super().send_head()
        size=path.stat().st_size;match=re.fullmatch(r"bytes=(\d*)-(\d*)",header.strip())
        if not match or not any(match.groups()) or not size:
            self.send_error(416,"Invalid byte range");return None
        a,b=match.groups()
        if a:start=int(a);end=min(size-1,int(b) if b else size-1)
        else:start=max(0,size-int(b));end=size-1
        if start<0 or start>=size or end<start:
            self.send_response(416);self.send_header("Content-Range",f"bytes */{size}");self.send_header("Content-Length","0");self.end_headers();return None
        try:stream=path.open("rb")
        except OSError:self.send_error(404);return None
        self.byte_range=(start,end)
        self.send_response(206);self.send_header("Content-Type",self.guess_type(str(path)))
        self.send_header("Accept-Ranges","bytes");self.send_header("Content-Range",f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length",str(end-start+1));self.end_headers()
        stream.seek(start);return stream

    def end_headers(self):
        if not getattr(self,"byte_range",None):self.send_header("Accept-Ranges","bytes")
        super().end_headers()

    def copyfile(self,source,output):
        if self.byte_range is None:return super().copyfile(source,output)
        remaining=self.byte_range[1]-self.byte_range[0]+1
        while remaining:
            chunk=source.read(min(64*1024,remaining))
            if not chunk:break
            output.write(chunk);remaining-=len(chunk)


def server(root,port=0):
    return http.server.ThreadingHTTPServer(("127.0.0.1",port),functools.partial(ReportHandler,directory=str(Path(root).resolve())))


def report_entry(root,entry):
    root=Path(root).resolve();path=(root/entry).resolve()
    if not path.is_relative_to(root) or not path.is_file():raise ValueError('Entry must be an existing file inside the served project directory')
    return path.relative_to(root).as_posix()


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("run");parser.add_argument("--port",type=int,default=3021)
    parser.add_argument('--entry',default='report.html',help='Relative report path, e.g. diagnosis/diagnostics.html under a shared project root')
    args=parser.parse_args();root=Path(args.run).resolve()
    try:entry=report_entry(root,args.entry)
    except ValueError as exc:raise SystemExit(str(exc))
    with server(root,args.port) as http:
        print(f"http://localhost:{http.server_port}/{quote(entry)}",flush=True)
        try:http.serve_forever()
        except KeyboardInterrupt:pass
