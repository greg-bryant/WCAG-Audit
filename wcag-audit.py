###############
# wcag-audit.py
#
# Server-side software for wcag-audit.appspot.com
#
# Copyright 2015 Greg Bryant with
#  John Fuller, Joseph Boland, Seth May,
#  Noah Talmadge, and Bryan Adams --
#  of the University of Oregon, College of Education
#  
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License. 
#
 
import logging
import os
import cgi
import webapp2
import time
import urllib2
import re
import json

from google.appengine.ext import db
from google.appengine.ext.webapp import template

# ----------------------------------
#
# schema for data: the url, a clean url for sorting,
# the version of auditor this report came from,
# the JSON report, and the time it was sent to
# this repository.
#
class Audit(db.Model):
  url = db.StringProperty()
  no_prefix_url = db.StringProperty()
  auditor_version = db.StringProperty()
  report = db.TextProperty()
  timestamp = db.DateTimeProperty(auto_now_add=True)


# ----------------------------------
# 
# render the home page
# list of all the urls (audit groups)
#
def render_home():
  template_values = {}

  # get the audits, sorted by url name
  audits = db.GqlQuery(
    "select * from Audit " +
    " order by no_prefix_url asc")

  # final array of urls (audit groups)
  audit_groups = []

  # url subject of the current audit group
  current_url = ''

  for audit in audits:
    if current_url != audit.url:
     new_audit_group = {
        'no_prefix_url': audit.no_prefix_url,
        'url_safe':urllib2.quote(audit.url, safe='')
     }
     audit_groups.append(new_audit_group)
     current_url = audit.url
     
  template_values['audit_groups'] = audit_groups
  template_values['group'] = False

  # render and return page
  path = os.path.join(os.path.dirname(__file__), 'index.html')
  return(template.render(path, template_values))

# ----------------------------------
#
# render the 'audit group' page
# (the detail page for each url)
#
def render_group(encoded_url):
  template_values = {}

  # get all the audits for this url
  audits = db.GqlQuery(
    "select * from Audit where url = :1 " +
    " order by timestamp desc", urllib2.unquote(encoded_url))

  # the audit group we're building
  audit_group = []

  # all of these audits' error totals, used by the chart
  total_array = []

  for audit in audits:

     # load audit report's JSON into python
     audit_data = json.loads(audit.report)
     total = count_failures(audit_data)

     new_audit = {
        'url': audit.url,
        'report': audit_data,
        'timestamp': audit.timestamp,
        'errors': total
     }
     audit_group.append(new_audit)
     total_array.append(total)

  # I want the chart order to be the
  # reverse of the list of reports
  total_array.reverse()

  template_values['audit_group'] = audit_group
  template_values['total_array'] = total_array
  template_values['group'] = True

  # render and return page
  path = os.path.join(os.path.dirname(__file__), 'index.html')
  return(template.render(path, template_values))

# ----------------------------------
#
def count_failures (data):
     total = 0
     for result in data['results']:
        total = total + int(result['failures'])
     return total

# ----------------------------------
#
# home page handler
#
class HomePage(webapp2.RequestHandler):
  def get(self):
     self.response.out.write(render_home())

# ----------------------------------
#
# audit group page handler
#
class AuditGroup(webapp2.RequestHandler):
  def get(self, encoded_url):
     self.response.out.write(render_group(encoded_url))

# ----------------------------------
#
# audit data coming from our modified chrome extension
#
class LogAudit(webapp2.RequestHandler):
  def post(self):
    audit = Audit()

    audit.url = urllib2.unquote(self.request.get('url'))
    audit.auditor_version = urllib2.unquote(self.request.get('auditor_version'))
    s = audit.url
    s = re.sub(r'^http://www\.','',s,flags=re.MULTILINE)
    s = re.sub(r'^https://www\.','',s,flags=re.MULTILINE)
    s = re.sub(r'^http://','',s,flags=re.MULTILINE)
    s = re.sub(r'^https://','',s,flags=re.MULTILINE)
    audit.no_prefix_url = s
    audit.report = urllib2.unquote(self.request.get('report'))
    audit.put()

    self.redirect('/')

# ----------------------------------
#
# routing
#
app = webapp2.WSGIApplication(
                                     [('/', HomePage),
                                      ('/group/(.*)', AuditGroup),
                                      ('/log_audit/', LogAudit)],
                                     debug=True)

