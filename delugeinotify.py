#!/usr/bin/env python
# Watches directories for torrent files (inotify)
# and adds them to Deluge.

# Watches:
#  key = Path to watch,
#  torrents: Path to move torrent file to, default is to leav it where is is
#  symlinks: Symlinks a data directory here

WATCHES = {
	'/storage/ge01': {
		'torrents': '/storage/ge01/bittorrent/torrents/'
	},

	'/storage/ge02': {
		'torrents': '/storage/ge02/bittorrent/torrents/'
	},

	'/storage/ch01/bittorrent': { },

	'/storage/ch02/musik': {
		'torrents': '/storage/ch02/bittorrent/torrents',
		'symlinks': '/storage/ch02/bittorrent/sorted'
	},

	'/storage/ch02/bittorrent/random': {},
}

import sys
import os
import time

import libtorrent as lt
from pyinotify import *
from deluge.ui.client import sclient


sclient.set_core_uri()

class DelugeNotifier(ProcessEvent):
	def __init__(self, watches):
		self.watches = watches
		self.moves = {}

	def addtorrent(self, torrent, path):
		t = [torrent.decode('utf8', 'ignore')]
		i = [{"download_location": path.decode('utf8', 'ignore')}]

		print 'Adding torrent: %s (%s)' % (os.path.basename(torrent), path)

		try:
			sclient.add_torrent_file(t, i)
		except:
			print 'Invalid torrent'

	def torrentinfo(self, path):
		e = lt.bdecode(open(path, 'rb').read())
		info = lt.torrent_info(e)

		return info

	def findwatch(self, path):
		for name, watch in self.watches.items():
			if path.startswith(name):
				return watch

		return False

	def symlink(self, source, target):
		if not os.path.islink(target):
			print 'Symlink %s -> %s' % (source, target)
			os.symlink(source, target)

	def process_IN_DELETE(self, event):
		pass

	def process_IN_MOVED_FROM(self, event):
		if not event.dir:
			return False

		self.moves[event.cookie] = event

	def process_IN_MOVED_TO(self, event):
		if not event.cookie in self.moves:
			return False

		source = self.moves[event.cookie]
		del self.moves[event.cookie]

		torrent_ids = sclient.get_session_state()
		for id in torrent_ids:
			info = sclient.get_torrent_status(id, ['name', 'save_path'])
			savepath = info['save_path']
			name = info['name']

			if savepath.startswith(source.pathname.decode('utf8', 'ignore')):
				target = savepath.replace(source.pathname.decode('utf8', 'ignore'), event.pathname.decode('utf8', 'ignore'))

				print 'Updating torrent (%s): %s -> %s' % (name, savepath, target)
				sclient.pause_torrent([id])
				time.sleep(2)
				sclient.set_torrent_options([id], { 'download_location': target })
				time.sleep(2)
				sclient.resume_torrent([id])


	def process_IN_CLOSE_WRITE(self, event):
		if not event.name.endswith('.torrent'):
			return False

		for name, watch in self.watches.items():
			if 'torrents' in watch:
				if os.path.normpath(watch['torrents']) == os.path.normpath(event.path.decode('utf8', 'ignore')):
					return False


		watch = self.findwatch(event.path)

		if watch == False:
			return False

		if 'torrents' in watch:
			torrentpath = os.path.join(watch['torrents'], event.name)
			os.rename(event.pathname, torrentpath)
		else:
			torrentpath = event.pathname

		time.sleep(2)

		if 'symlinks' in watch:
			info = self.torrentinfo(torrentpath)
			source = os.path.join(event.path, info.name())
			target = os.path.join(watch['symlinks'], event.name.strip('.torrent'))

			self.symlink(source, target)

		self.addtorrent(torrentpath, event.path)

	def process_default(self, event):
		pass

wm = WatchManager()
mask = ALL_EVENTS
notifier = Notifier(wm, DelugeNotifier(WATCHES))


for path, watch in WATCHES.items():
	print 'Watching %s' % path
	wm.add_watch(path, mask, rec = True, auto_add = True)


print 'Watches setup'
notifier.loop()
