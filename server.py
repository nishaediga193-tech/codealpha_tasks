import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

class RangeRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()

    def send_head(self):
        if 'Range' not in self.headers:
            self.range = None
            return super().send_head()

        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().send_head()

        fsize = os.path.getsize(path)
        range_header = self.headers['Range']
        m = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if not m:
            return super().send_head()

        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else fsize - 1
        end = min(end, fsize - 1)
        length = end - start + 1

        try:
            f = open(path, 'rb')
            f.seek(start)
        except OSError:
            self.send_error(404, "File not found")
            return None

        self.send_response(206)
        ctype = self.guess_type(path)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Range', f'bytes {start}-{end}/{fsize}')
        self.send_header('Content-Length', str(length))
        self.send_header('Last-Modified', self.date_time_string(os.path.getmtime(path)))
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()
        self.range = (start, length)
        return f

    def copyfile(self, source, outputfile):
        if not hasattr(self, 'range') or not self.range:
            super().copyfile(source, outputfile)
            return

        start, length = self.range
        rem = length
        bufsize = 64 * 1024
        while rem > 0:
            read_size = min(bufsize, rem)
            data = source.read(read_size)
            if not data:
                break
            try:
                outputfile.write(data)
            except (ConnectionResetError, BrokenPipeError):
                break
            rem -= len(data)

def run(port=8000):
    server = ThreadingHTTPServer(('0.0.0.0', port), RangeRequestHandler)
    print(f"Server started on http://localhost:{port} with HTTP Range (206) video streaming support.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    run()
