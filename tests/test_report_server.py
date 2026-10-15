"""Native video scrubbing requires real HTTP byte-range responses."""
import http.client
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from serve_report import server


class RangeTests(unittest.TestCase):
    def request(self,range_header):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,"video.mp4").write_bytes(bytes(range(100)))
            with server(folder) as httpd:
                worker=threading.Thread(target=httpd.serve_forever);worker.start()
                try:
                    connection=http.client.HTTPConnection('127.0.0.1',httpd.server_port)
                    connection.request('GET','/video.mp4',headers={'Range':range_header})
                    response=connection.getresponse();result=response.status,response.getheader('Content-Range'),response.read();connection.close()
                finally:httpd.shutdown();worker.join()
            return result

    def test_exact_video_range(self):
        status,header,body=self.request('bytes=40-49')
        self.assertEqual((status,header,body),(206,'bytes 40-49/100',bytes(range(40,50))))

    def test_suffix_video_range(self):
        status,header,body=self.request('bytes=-10')
        self.assertEqual((status,header,body),(206,'bytes 90-99/100',bytes(range(90,100))))

    def test_outside_file_range_rejected(self):
        status,header,body=self.request('bytes=100-200')
        self.assertEqual((status,header,body),(416,'bytes */100',b''))


if __name__=="__main__":unittest.main()
