import tornado.httpserver, tornado.ioloop, tornado.options, tornado.web, os.path, random, string
from tornado.options import define, options
import tornado.httpserver
import tornado.gen
import tornado.process

from io import BytesIO
import contextlib
import wave
from arabic_dialect_identification.acoustic import acoustic_identification4
import json
import logging
import time
import os
import os.path
import argparse
# import magic
# import mimetypes
# from pydub import AudioSegment


define("port", default=8889, help="run on the given port", type=int)
define('debug', type=bool, default=False, help="enable debug, default False")
define('host', type=str, default="127.0.0.1", help="http listen host, default 127.0.0.1")
# define('port', type=int, default=8080, help="http listen port, default 8080")
define('storage_path', type=str, default="/home/qcri/dialectid_api/uploads/", help="file storage path")
# define("certfile", default="", help="certificate file for secured SSL connection")
# define("keyfile", default="", help="key file for secured SSL connection")
options.parse_command_line()
# args = parser.parse_args()

logger = logging.getLogger('fileserver')

project_dir_path = os.path.abspath(os.path.dirname(__file__))

if not os.path.exists(options.storage_path):
    os.mkdir(options.storage_path)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            # (r"/", IndexHandler),
            (r"/", UploadHandler, dict(protocol="https"))
            # (r"/upload", IndexHandler)
            # (r"/api/upload", tornado.web.StaticFileHandler, {'path': './api', 'default_filename': 'index.html'})

        ]
        tornado.web.Application.__init__(self, handlers)

    # def send_status_update_single(self):
    #     status = dict(num_workers_available=len(self.available_workers),
    #                   num_requests_processed=self.num_requests_processed)
    #     # ws.write_message(json.dumps(status))
    #
    # def send_status_update(self):
    #     for ws in self.status_listeners:
    #         self.send_status_update_single(ws)


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index_api.html")

class LinuxUtils(object):

    @staticmethod
    @tornado.gen.coroutine
    def mv(src, dest):
        cmd = ["mv", src, dest]
        proc = tornado.process.Subprocess(cmd)
        ret = yield proc.wait_for_exit(raise_error=False)
        raise tornado.gen.Return(ret == 0)

    @staticmethod
    @tornado.gen.coroutine
    def rm(file):
        cmd = ["rm", file]
        proc = tornado.process.Subprocess(cmd)
        ret = yield proc.wait_for_exit(raise_error=False)
        raise tornado.gen.Return(ret == 0)

class UploadHandler(tornado.web.RequestHandler):

    def set_default_headers(self):
        self.set_header("Content-Type", 'application/json')
        # self.set_header("Access-Control-Allow-Origin", "*")
        # self.set_header("Access-Control-Allow-Headers", "content-type")
        # self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        # self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, PATCH, PUT')

    @tornado.gen.coroutine
    def post(self):
        print('in------------upload')
        file1 = self.request.files['file1'][0]

        original_fname = file1['filename']
        print(original_fname)
        extension = os.path.splitext(original_fname)[1]
        fname = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))
        final_filename= fname+extension
        output_file = open(os.path.join(options.storage_path, final_filename), 'wb')
        output_file.write(file1['body'])
        raw_file_name =options.storage_path + final_filename

        # if extension == 'wav':
        a, b, c = str(time.time()).partition('.')
        time_stamp = ''.join([a, b, c.zfill(2)])
        memory_buffer = BytesIO()
        raw_file_obj=''
        # if extension == 'wav':
        #     sound = AudioSegment.from_wav(raw_file_name)  # can do same for mp3 and other formats
        #
        #     raw_file_obj = sound._data  # returns byte string
        #     # raw_file_obj = open(raw, 'rb', os.O_NONBLOCK)
        print(extension, "2")
        xx=""
        index=0
        acoustic_scores={}
        if extension=='.raw' or extension=='.wav' :
            # if extension == 'raw':
            print(extension)
            raw_file_obj = open(raw_file_name, 'rb', os.O_NONBLOCK)
            with contextlib.closing(wave.open(memory_buffer, 'wb')) as wave_obj:
                wave_obj.setnchannels(1)
                wave_obj.setframerate(16000)
                wave_obj.setsampwidth(2)
                # raw_file_obj.seek(-640000, 2)
                wave_obj.writeframes(raw_file_obj.read())
            memory_buffer.flush()
            memory_buffer.seek(0)

            acoustic_scores = acoustic_identification4.dialect_estimation(memory_buffer)
            index = 1
        # elif  extension=='.wav' :
        #     acoustic_scores = acoustic_identification4.dialect_estimationWav(raw_file_name)
        #     # if extension == 'raw':
        #
        #     index = 1

        if index == 1:
            acoustic_weight = 1.0  # - lexical_weight
            # weighted_lexical = {dialect: value * lexical_weight for dialect, value in lexical_scores.items()}
            weighted_acoustic = {dialect: value * acoustic_weight for dialect, value in acoustic_scores.items()}

            # did_scores = {key: weighted_lexical[key] + weighted_acoustic[key] for key in [u'EGY', u'GLF', u'LAV',
            #                                                                               u'MSA', u'NOR']}

            did_scores = {key: weighted_acoustic[key] for key in
                          ['ALG', 'EGY', 'IRA', 'JOR', 'KSA', 'KUW', 'LEB', 'LIB', 'MAU', 'MOR', 'OMA',
                           'PAL', 'QAT', 'SUD', 'SYR', 'UAE', 'YEM']}
            # did_scores = {key: weighted_acoustic[key] for key in [u'ALG', u'EGY',u'IRA', u'JOR', u'KSA', u'KUW', u'LEB', u'LIB', u'MAU', u'MOR', u'OMA', u'PAL', u'QAT', u'SUD', u'SYR', u'UAE', u'YEM']}
            print(did_scores)
            json_list = list()
            # json_list.append(text)
            # json_list.append(utterance)
            json_dict = {'final_score': did_scores}
            # print(did_scores)
            # json_dict = {'lexical_score': lexical_scores, 'acoustic_score': acoustic_scores, 'final_score': did_scores}
            json_list.append(json_dict)
            text_file = os.path.join("uploads/", time_stamp + '.json')
            with open(text_file, mode='w') as json_obj:
                json.dump(json_list, json_obj)
            # return json_obj
                # event['result']['hypotheses'].append(did_scores)

            # return did_scores

            xx=json.dumps(json_list)
        print(xx)
        self.write(xx)
        # self.finish("file" + final_filename + " is uploaded\n"+' Output: '+xx  )
        # return xx

    def options(self, *args, **kwargs):
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.set_header('Access-Control-Max-Age', 1000)
        # note that '*' is not valid for Access-Control-Allow-Headers
        self.set_header('Access-Control-Allow-Headers',
                        'origin, x-csrftoken, content-type, accept, User-Id, Content-Id')
        
def main():
    settings = {
        'debug': True,
        'autoreload': True,

        # 'static_path': '/home/qcri/dialectid_api/'
        # other stuff
    }
    http_server = tornado.web.Application([
        # (r"/", IndexHandler),
        (r"/", UploadHandler)

    ], **settings)

    # ssl_options = {
    #                   "certfile": "/etc/ssl/wildcard.qcri.org.2020.crt",
    #                   "keyfile": "/etc/ssl/wildcard.qcri.org.key"
    #
    #               }

    # if options.certfile and options.keyfile:
    # ssl_options = {
    #         "certfile": options.certfile,
    #         "keyfile": options.keyfile,
    #     }
    # server = tornado.httpserver.HTTPServer(http_server, xheaders=True,ssl_options=ssl_options)
    server = tornado.httpserver.HTTPServer(http_server, xheaders=True)
    # server = http_server
    logging.info("Using SSL for serving requests")
    server.listen(options.port)
    # server.listen(443)
    # else:
    #     server.listen(options.port)

    # http_server = tornado.httpserver.HTTPServer(tornado.web.Application([
    #     # (r"/", IndexHandler),
    #     (r"/", UploadHandler)
    #
    # ], **settings),ssl_options = {
    #                   "certfile": "/etc/ssl/wildcard.qcri.org.2020.crt",
    #                   "keyfile": "/etc/ssl/wildcard.qcri.org.key"
    #               })

    # http_server = tornado.httpserver.HTTPServer(Application([(r"/", IndexHandler),
    #         (r"/upload", UploadHandler)]), debug=True,**settings)
    # http_server.listen(options.port)
        # ,address=options.host)
    tornado.ioloop.IOLoop.instance().start()
    
if __name__ == "__main__":
    main()
