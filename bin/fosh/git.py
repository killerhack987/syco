#! /usr/bin/env python

import general

def git_commit(comment):
  '''
  Commit the fosh folder to the github repository.
  '''
  general.shell_exec("find /opt/fosh/ -iname '*.pyc' -delete")
  general.shell_exec("cd /opt/fosh;git add *")
  general.shell_exec("cd /opt/fosh;git commit -a -m'%s'" % comment)
  general.shell_exec("git push origin")