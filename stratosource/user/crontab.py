# Copyright 2008, Martin Owens.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Rewritten from scratch, but based on the code from gnome-schedual gui package by:
# - Philip Van Hoof <me at pvanhoof dot be>
# - Gaute Hope <eg at gaute dot vetsj dot com>
# - Kristof Vansant <de_lupus at pandora dot be>
#

"""
Example Use:

from crontab import CronTab

tab = CronTab()
cron = tab.new(command='/usr/bin/echo')

cron.minute().during(5,50).every(5)
cron.hour().every(4)

cron2 = tab.new(command='/foo/bar',comment='SomeID')
cron2.every_reboot()

list = tab.find('bar')
cron3 = list[0]
cron3.clear()
cron3.minute().every(1)

print unicode(tab.render())

for cron4 in tab.find('echo'):
	print cron4

for cron5 in tab:
	print cron5

tab.remove_all('echo')

t.write()
"""

import os, re, sys
import tempfile

version = '0.8'
command = "/usr/bin/crontab"
itemrex = re.compile('^\s*([^@#\s]+)\s([^@#\s]+)\s([^@#\s]+)\s([^@#\s]+)\s([^@#\s]+)\s([^#\n]*)(\s+#\s*([^\n]*)|$)')
specrex = re.compile('@(\w+)\s([^#\n]*)(\s+#\s*([^\n]*)|$)')
devnull = ">/dev/null 2>&1"


month_enum = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
week_enum  = ['sun','mon','tue','wed','thu','fri','sat','sun']

specials = {
	"reboot"  : '@reboot',
	"hourly"  : '0 * * * *',
	"daily"   : '0 0 * * *',
	"weekly"  : '0 0 * * 0',
	"monthly" : '0 0 1 * *',
	"yearly"  : '0 0 1 1 *',
	"annually": '0 0 1 1 *',
	"midnight": '0 0 * * *'
}

s_info = [
	{ 'name' : 'Minutes',      'max' : 59, 'min' : 0 },
	{ 'name' : 'Hours',        'max' : 23, 'min' : 0 },
	{ 'name' : 'Day of Month', 'max' : 31, 'min' : 1 },
	{ 'name' : 'Month',        'max' : 12, 'min' : 1, 'enum' : month_enum },
	{ 'name' : 'Day of Week',  'max' : 7,  'min' : 0, 'enum' : week_enum },
]

class CronTab(list):
	def __init__(self, user=None):
		self.user  = user
		self.root  = ( os.getuid() == 0 )
		self.lines = []
		self.crons = []
		self.read()

	def user_execute(self):
		if self.user:
			return ' -u %s' % str(self.user)
		return ''

	def read(self):
		for line in os.popen(self.read_execute()).readlines():
			cron = CronItem(line)
			if cron.isValid():
				self.crons.append(cron)
				self.lines.append(cron)
			else:
				self.lines.append(line.replace('\n',''))
	
	def read_execute(self):
		return "%s -l%s" % (command, self.user_execute())

	def write(self):
		fd, path = tempfile.mkstemp()
		fh = os.fdopen(fd, 'w')
		fh.write(self.render())
		fh.close()
		# Add the entire crontab back to the user crontab
		os.system("%s -r" % (command))
		os.system(self.write_execute(path))
		os.unlink(path)

	def write_execute(self, path):
		return "%s %s%s" % (command, path, self.user_execute())

	def render(self):
		"""
		Internal method for rendering a crontab.
		"""
		crons = []
		for cron in self.lines:
			if type(cron) == CronItem and not cron.isValid():
				continue
			crons.append(unicode(cron))
		return '\n'.join(crons) + "\n"

	def add(self, item):
		self.crons.append(item)
		self.lines.append(item)
		return item

	def new(self, command='', comment=''):
		"""
		Create a new cron with a command and comment. Returns the new object.
		"""
		item = CronItem(command=command,meta=comment)
		return add(item)

	def find_command(self, command):
		"""
		Return a list of crons using a command.
		"""
		result = []
		for cron in self.crons:
			if cron.command.match(command):
				result.append(cron)
		return result

	def remove_all(self, command):
		"""
		Removes all crons using the stated command.
		"""
		l = self.find_command(command)
		for c in l:
			self.remove(c)

	def remove(self, item):
		"""
		Remove a selected cron from the crontab.
		"""
		self.crons.remove(item)
		self.lines.remove(item)

	def __iter__(self):
		return self.crons.__iter__()


class CronItem:
	def __init__(self, line=None, command='', meta=''):
		self.command = CronCommand(unicode(command))
		self._meta   = meta
		self.valid   = False
		self.slices  = []
		self.special = False
		self.set_slices()
		self.raw_line = line
		if line:
			self.parse(line)


	def parse(self, line):
		self.raw_line = line
		result = itemrex.findall(line)
		if result:
			o = result[0]
			self.command = CronCommand(o[5])
			self._meta   = o[7]
			self.set_slices( o )
			self.valid = True
		elif line.find('@') < line.find('#') or line.find('#')==-1:
			result = specrex.findall(line)
			if result and specials.has_key(result[0][0]):
				o = result[0]
				self.command = CronCommand(o[1])
				self._meta   = o[3]
				value = specials[o[0]]
				if value.find('@') > 1:
					self.special = value
				else:
					self.set_slices( value.split(' ') )
				self.valid = True


	def set_slices(self, o=[None,None,None,None,None]):
		self.slices = []
		for i in range(0,5):
			self.slices.append(CronSlice(value=o[i], **s_info[i]))

	def isValid(self):
		return self.valid


	def render(self):
		time = ''
		if not self.special:
			slices = []
			for i in range(0,5):
				slices.append(unicode(self.slices[i]))
			time = ' '.join(slices)
		if self.special or time in specials.values():
			if self.special:
				time = self.special
			else:
				time = "@%s" % specials.keys()[specials.values().index(time)]

		result = "%s %s" % (time, unicode(self.command))
		if self.meta():
			result += " # " + self.meta()
		return result


	def meta(self, value=None):
		if value:
			self._meta = value
		return self._meta

	def every_reboot(self):
		self.special = '@reboot'


	def clear(self):
		self.special = None
		for slice in self.slices:
			slice.clear()


	def minute(self):
		return self.slices[0]
	def hour(self):
		return self.slices[1]
	def dom(self):
		return self.slices[2]
	def month(self):
		return self.slices[3]
	def dow(self):
		return self.slices[4]

	def __str__(self):
		return self.__unicode__()

	def __unicode__(self):
		return self.render()



class CronSlice:
	def __init__(self, name, min, max, enum=None, value=None):
		self.name  = name
		self.min   = min
		self.max   = max
		self.enum  = enum
		self.parts = []
		self.value(value)


	def value(self, value=None):
		if value:
			self.parts = []
			for part in value.split(','):
				if part.find("/") > 0 or part.find("-") > 0 or part == '*':
					self.parts.append( self.get_range( part ) )
				else:
					if self.enum and part.lower() in self.enum:
						part = self.enum.index(part.lower())
					try:
						self.parts.append( int(part) )
					except:
						raise ValueError, 'Unknown cron time part for %s: %s' % (self.name, part)		
		return self.render()


	def render(self):
		result = []
		for part in self.parts:
			result.append(unicode(part))
		if not result:
			return '*'
		return ','.join(result)

	def __str__(self):
		return self.__unicode__()

	def __unicode__(self):
		return self.render()


	def every(self, n):
		# Every X units
		self.parts = [ self.get_range( '*/%d' % int(n) ) ]


	def on(self, *n):
		# On the time
		self.parts += n


	def during(self, fro, to):
		range = self.get_range( "%s-%s" % (str(fro), str(to)) )
		self.parts.append( range )
		return range

	def clear(self):
		self.parts = []

	def get_range(self, range):
		return CronRange( self, range )


class CronRange:
	def __init__(self, slice, range=None):
		self.slice = slice
		self.seq   = 1
		if not range:
			range = '*'
		self.parse(range)


	def parse(self, value):
		if value.find('/') > 0:
			value, self.seq = value.split('/')
		if value.find('-') > 0:
			a,b = value.split('-')
			self.fro = self.clean_value(a)
			self.to  = self.clean_value(b)
		elif value == '*':
			self.fro = self.slice.min
			self.to  = self.slice.max
		else:
			raise ValueError, 'Unknown cron range value %s' % value


	def render(self):
		value = '*'
		if self.fro > self.slice.min or self.to < self.slice.max:
			value = "%d-%d" % (int(self.fro), int(self.to))
		if int(self.seq) != 1:
			value += "/%d" % (int(self.seq))
		return value


	def clean_value(self, value):
		if self.slice.enum and str(value).lower() in self.slice.enum:
			value = self.slice.enum.index(str(value).lower())
		try:
			value = int(value)
			if value >= self.slice.min and value <= self.slice.max:
				return value
		except:
			pass
		raise ValueError, 'Invalid range value %s' % str(value)


	def every(self, value):
		self.seq = int(value)

	def __str__(self):
		return self.__unicode__()

	def __unicode__(self):
		return self.render()



class CronCommand:
	def __init__(self, line):
		self.command = line

	def match(self, command):
		if command in self.command:
			return True
		return False

	def __str__(self):
		return self.__unicode__()

	def __unicode__(self):
		return self.command

