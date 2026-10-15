#!/usr/bin/env python3
"""Record real Impress GUI playback on a private X11 display; never render a substitute."""
import argparse
import hashlib
import json
import math
import os
import platform
import re
import shutil
import signal
import subprocess
import time
from datetime import datetime,timezone
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def toolchain(root):
    env=os.environ.copy()
    if root:
        root=Path(root).resolve()/"root";office=root/"usr/lib/libreoffice"
        env.update(URE_BOOTSTRAP=(office/"program/fundamentalrc").as_uri(),UNO_PATH=str(office/"program"),
                   LD_LIBRARY_PATH=str(office/"program")+":"+str(root/"usr/lib/x86_64-linux-gnu")+":"+env.get("LD_LIBRARY_PATH",""),
                   XDG_DATA_DIRS=str(root/"usr/share")+":/usr/local/share:/usr/share",
                   XDG_CONFIG_DIRS=str(root/"etc/xdg")+":/etc/xdg")
        tools={"office":str(office/"program/soffice"),"xvfb":str(root/"usr/bin/Xvfb"),
               "xdotool":str(root/"usr/bin/xdotool"),"openbox":str(root/"usr/bin/openbox")}
    else:
        tools={"office":shutil.which("libreoffice") or shutil.which("soffice"),
               "xvfb":shutil.which("Xvfb"),"xdotool":shutil.which("xdotool"),"openbox":shutil.which("openbox")}
    tools.update(ffmpeg=shutil.which("ffmpeg"),ffprobe=shutil.which("ffprobe"))
    if any(not p or not Path(p).is_file() for p in tools.values()):
        raise ValueError("GUI Impress, Xvfb, openbox, xdotool, FFmpeg and ffprobe are required")
    env["SAL_USE_VCLPLUGIN"]="gen"
    return tools,env


def stop(process):
    if process and process.poll() is None:
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL);process.wait()


def record(args):
    deck=Path(args.pptx).resolve();out=Path(args.out).resolve()
    if not deck.is_file() or deck.suffix.lower()!=".pptx":raise ValueError("A PPTX file is required")
    if not math.isfinite(args.seconds) or not math.isfinite(args.show_after) or args.seconds<=args.show_after or args.show_after<.5:
        raise ValueError("Recording must extend beyond a show delay of at least 0.5s")
    if not all(math.isfinite(t) and args.show_after<t<args.seconds for t in args.click_at):
        raise ValueError("Clicks must fall after F5 and before recording ends")
    if not 1<=args.fps<=120 or args.width<=0 or args.height<=0 or args.width%2 or args.height%2:
        raise ValueError("Use even, positive screen dimensions and fps 1–120")
    out.mkdir(parents=True,exist_ok=True);video=out/"player-recording.mp4"
    if video.exists():raise FileExistsError("Preserve the previous recording; choose a new output folder")
    tools,env=toolchain(args.tools_root)
    version=subprocess.check_output([tools["office"],"--version"],env=env,text=True).strip()
    number=next((i for i in range(91,120) if not Path(f"/tmp/.X11-unix/X{i}").exists() and not Path(f"/tmp/.X{i}-lock").exists()),None)
    if number is None:raise ValueError("No unused private X display")
    display=f":{number}";env["DISPLAY"]=display
    source_sha=digest(deck);processes=[];handles=[];actions=[]
    input_folder=out/"input";input_folder.mkdir(exist_ok=True)
    playback_copy=input_folder/deck.name
    shutil.copy2(deck,playback_copy)
    stage=out/"player-recording.partial.mp4"
    def spawn(command,log):
        handle=(out/log).open("w");handles.append(handle)
        p=subprocess.Popen(command,env=env,stdout=handle,stderr=handle,start_new_session=True)
        processes.append(p);return p
    def key(value):subprocess.run([tools["xdotool"],"key",value],env=env,check=True)
    try:
        xvfb=spawn([tools["xvfb"],display,"-screen","0",f"{args.width}x{args.height}x24","-dpi","96","-nolisten","tcp","-noreset"],"xvfb.log")
        deadline=time.monotonic()+10
        while not Path(f"/tmp/.X11-unix/X{number}").exists():
            if xvfb.poll() is not None or time.monotonic()>deadline:raise RuntimeError("Private X display failed")
            time.sleep(.05)
        spawn([tools["openbox"],"--sm-disable"],"window-manager.log")
        profile=out/"player-profile"
        office=spawn([tools["office"],"-env:UserInstallation="+profile.as_uri(),"--norestore","--nologo",
                      "--nofirststartwizard","--view","--impress",str(playback_copy)],"player.log")
        deadline=time.monotonic()+45;window=None
        while time.monotonic()<deadline:
            result=subprocess.run([tools["xdotool"],"search","--onlyvisible","--name",re.escape(deck.name)],env=env,capture_output=True,text=True)
            if result.returncode==0 and result.stdout.strip():
                window=result.stdout.splitlines()[0];break
            if office.poll() is not None:raise RuntimeError("GUI player exited before opening the presentation")
            time.sleep(.1)
        if window is None:raise RuntimeError("Presentation window did not appear; inspect player.log")
        subprocess.run([tools["xdotool"],"windowactivate","--sync",window],env=env,check=True)
        subprocess.run([tools["xdotool"],"mousemove",str(args.width-2),str(args.height-2)],env=env,check=True)
        start=time.monotonic()
        capture=spawn([tools["ffmpeg"],"-hide_banner","-nostdin","-y","-f","x11grab","-draw_mouse","0",
                       "-video_size",f"{args.width}x{args.height}","-framerate",str(args.fps),"-i",display,
                       "-t",str(args.seconds),"-c:v","libx264","-preset","veryfast","-crf","18","-threads","4",
                       "-pix_fmt","yuv420p","-movflags","+faststart",str(stage)],"capture.log")
        schedule=[(args.show_after,"F5"),*((t,"space") for t in sorted(args.click_at))]
        for at,value in schedule:
            while time.monotonic()-start<at:
                if capture.poll() is not None:raise RuntimeError("Screen capture stopped early")
                time.sleep(.025)
            elapsed=time.monotonic()-start;key(value)
            actions.append({"at_wall_seconds":elapsed,"key":value})
        if capture.wait()!=0:raise RuntimeError("Screen capture failed")
        if digest(deck)!=source_sha or digest(playback_copy)!=source_sha:
            raise RuntimeError("Presentation changed during playback")
        stage.replace(video)
        metadata=json.loads(subprocess.check_output([tools["ffprobe"],"-v","error","-show_entries",
            "stream=width,height,avg_frame_rate,r_frame_rate,nb_frames","-show_entries","format=duration","-of","json",str(video)],text=True))
        report={"origin":"native_desktop_screen_capture","is_pptx_playback_recording":True,
                "player":"LibreOffice Impress","version":version,"system":platform.platform(),
                "recorded_at":datetime.now(timezone.utc).isoformat(),"virtual_display":"Xvfb "+display,
                "capture_requested":{"width":args.width,"height":args.height,"fps":args.fps},
                "actual_video_metadata":metadata,"source_pptx":str(deck),"source_pptx_sha256":source_sha,
                "opened_copy":str(playback_copy),"opened_copy_sha256":source_sha,
                "recording":str(video),"recording_sha256":digest(video),"actions":actions,
                "status":"recorded_pending_visual_review",
                "scope":"Actual Impress GUI on a private X display; capture fps does not prove player redraw rate or WPS/PowerPoint compatibility"}
        (out/"playback-evidence.json").write_text(json.dumps(report,indent=2)+"\n")
        key("Escape");key("ctrl+q")
        try:office.wait(timeout=3)
        except subprocess.TimeoutExpired:pass
        return report
    finally:
        for process in reversed(processes):stop(process)
        for handle in handles:handle.close()


if __name__=="__main__":
    def terminate_recording(signum,frame):raise KeyboardInterrupt("Desktop recording terminated")
    signal.signal(signal.SIGTERM,terminate_recording)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pptx");parser.add_argument("--out",required=True)
    parser.add_argument("--tools-root");parser.add_argument("--seconds",type=float,default=35)
    parser.add_argument("--show-after",type=float,default=1)
    parser.add_argument("--click-at",type=float,action="append",default=[])
    parser.add_argument("--width",type=int,default=1920);parser.add_argument("--height",type=int,default=1080)
    parser.add_argument("--fps",type=int,default=60)
    print(json.dumps(record(parser.parse_args()),indent=2))
