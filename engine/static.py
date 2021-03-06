#!/usr/bin/env python
#
# Copyright 2016 Feei. All Rights Reserved
#
# Author:   Feei <wufeifei@wufeifei.com>
# Homepage: https://github.com/wufeifei/cobra
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the file 'doc/COPYING' for copying permission
#
import os
import sys
import re
import time
import subprocess
from pickup import directory
from utils import log
from app import db, CobraResults, CobraRules, CobraLanguages, CobraTaskInfo, CobraWhiteList


class Static:
    def __init__(self, directory_path=None, task_id=None, project_id=None):
        self.directory = directory_path
        self.task_id = task_id
        self.project_id = project_id

    def analyse(self):
        if self.directory is None:
            log.critical("Please set directory")
            sys.exit()
        log.info('Start code static analyse...')

        d = directory.Directory(self.directory)
        files = d.collect_files(self.task_id)
        log.info('Scan Files: {0}, Total Time: {1}s'.format(files['file_nums'], files['collect_time']))

        ext_language = {
            # Image
            '.jpg': 'image',
            '.png': 'image',
            '.bmp': 'image',
            '.gif': 'image',
            '.ico': 'image',
            '.cur': 'image',
            # Font
            '.eot': 'font',
            '.otf': 'font',
            '.svg': 'font',
            '.ttf': 'font',
            '.woff': 'font',
            # CSS
            '.css': 'css',
            '.less': 'css',
            '.scss': 'css',
            '.styl': 'css',
            # Media
            '.mp3': 'media',
            '.swf': 'media',
            # Execute
            '.exe': 'execute',
            '.sh': 'execute',
            '.dll': 'execute',
            '.so': 'execute',
            '.bat': 'execute',
            '.pl': 'execute',
            # Edit
            '.swp': 'tmp',
            # Cert
            '.crt': 'cert',
            # Text
            '.txt': 'text',
            '.csv': 'text',
            '.md': 'markdown',
            # Backup
            '.zip': 'backup',
            '.bak': 'backup',
            '.tar': 'backup',
            '.rar': 'backup',
            '.tar.gz': 'backup',
            '.db': 'backup',
            # Config
            '.xml': 'config',
            '.yml': 'config',
            '.spf': 'config',
            '.iml': 'config',
            '.manifest': 'config',
            # Source
            '.psd': 'source',
            '.as': 'source',
            # Log
            '.log': 'log',
            # Template
            '.template': 'template',
            '.tpl': 'template',
        }
        for ext in files:
            if ext in ext_language:
                log.info('{0} - {1}'.format(ext, files[ext]))
                continue
            else:
                log.info(ext)

        languages = CobraLanguages.query.all()

        rules = CobraRules.query.filter_by(status=1).all()
        extensions = None
        # `grep` (`ggrep` on Mac)
        grep = '/bin/grep'
        # `find` (`gfind` on Mac)
        find = '/bin/find'
        if 'darwin' == sys.platform:
            ggrep = ''
            gfind = ''
            for root, dir_names, file_names in os.walk('/usr/local/Cellar/grep'):
                for filename in file_names:
                    if 'ggrep' == filename or 'grep' == filename:
                        ggrep = os.path.join(root, filename)
            for root, dir_names, file_names in os.walk('/usr/local/Cellar/findutils'):
                for filename in file_names:
                    if 'gfind' == filename:
                        gfind = os.path.join(root, filename)
            if ggrep == '':
                log.critical("brew install ggrep pleases!")
                sys.exit(0)
            else:
                grep = ggrep
            if gfind == '':
                log.critical("brew install findutils pleases!")
                sys.exit(0)
            else:
                find = gfind

        for rule in rules:
            log.info('Scan rule id: {0} {1} {2}'.format(self.project_id, rule.id, rule.description))
            # Filters
            for language in languages:
                if language.id == rule.language:
                    extensions = language.extensions.split('|')
            if extensions is None:
                log.critical("Rule Language Error")
                sys.exit(0)

            # White list
            white_list = []
            ws = CobraWhiteList.query.filter_by(project_id=self.project_id, rule_id=rule.id, status=1).all()
            if ws is not None:
                for w in ws:
                    white_list.append(w.path)

            try:
                if rule.regex.strip() == "":
                    filters = []
                    for index, e in enumerate(extensions):
                        if index > 1:
                            filters.append('-o')
                        filters.append('-name')
                        filters.append('*' + e)
                    # Find Special Ext Files
                    param = [find, self.directory, "-type", "f"] + filters
                else:
                    filters = []
                    for e in extensions:
                        filters.append('--include=*' + e)

                    # Explode SVN Dir
                    filters.append('--exclude-dir=.svn')
                    filters.append('--exclude-dir=.cvs')
                    filters.append('--exclude-dir=.hg')
                    filters.append('--exclude-dir=.git')
                    filters.append('--exclude-dir=.bzr')
                    filters.append('--exclude=*.svn-base')
                    # -n Show Line number / -r Recursive / -P Perl regular expression
                    param = [grep, "-n", "-r", "-P"] + filters + [rule.regex, self.directory]

                # log.info(' '.join(param))
                p = subprocess.Popen(param, stdout=subprocess.PIPE)
                result = p.communicate()

                # Exists result
                if len(result[0]):
                    lines = str(result[0]).split("\n")
                    for line in lines:
                        line = line.strip()
                        if line == '':
                            continue
                        if rule.regex.strip() == '':
                            # Find
                            file_path = line.strip().replace(self.directory, '')
                            log.debug('File: {0}'.format(file_path))
                            vul = CobraResults(self.task_id, rule.id, file_path, 0, '')
                            db.session.add(vul)
                        else:
                            # Grep
                            line_split = line.replace(self.directory, '').split(':', 1)
                            file_path = line_split[0].strip()
                            code_content = line_split[1].split(':', 1)[1].strip()
                            line_number = line_split[1].split(':', 1)[0].strip()

                            if file_path in white_list or ".min.js" in file_path:
                                log.info("In white list or min.js")
                            else:
                                # Annotation
                                # # // /* *
                                match_result = re.match("(#)?(//)?(\*)?(/\*)?", code_content)
                                if match_result.group(0) is not None and match_result.group(0) is not "":
                                    log.info("In Annotation")
                                else:
                                    log.info('In Insert')
                                    exist_result = CobraResults.query.filter_by(task_id=self.task_id, rule_id=rule.id, file=file_path, line=line_number).first()
                                    if exist_result is not None:
                                        log.warning("Exists Result")
                                    else:
                                        log.debug('File: {0}:{1} {2}'.format(file_path, line_number, code_content))
                                        vul = CobraResults(self.task_id, rule.id, file_path, line_number, code_content)
                                        db.session.add(vul)
                                        log.info('Insert Results Success')
                    db.session.commit()
                else:
                    log.info('Not Found')

            except Exception as e:
                log.critical('Error calling grep: ' + str(e))

        # Set End Time For Task
        t = CobraTaskInfo.query.filter_by(id=self.task_id).first()
        t.status = 2
        t.file_count = files['file_nums']
        t.time_end = int(time.time())
        t.time_consume = t.time_end - t.time_start
        t.updated_at = time.strftime('%Y-%m-%d %X', time.localtime())
        try:
            db.session.add(t)
            db.session.commit()
        except Exception as e:
            log.critical("Set start time failed:" + e.message)

        log.info("Scan Done")
