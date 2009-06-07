#!/usr/bin/env python
# Searches in specified directory for files
# usable by torrents and adds them to Deluge.

# Usage: delugeimport.py <torrentpath> <searchpath>

import sys
import os

import libtorrent as lt
from deluge.ui.client import sclient

sclient.set_core_uri()

def add_torrent(torrent, path):
	t = [torrent]
	i = [{'download_location':  path}]

	print t
	print i

	sclient.add_torrent_file(t, i)


def compare(path, torrent):
	for file in	torrent['files']:
		try:
			stat = os.stat(os.path.join(path.decode('utf8', 'ignore'), file['filename']))

			if not stat.st_size == file['size']:
				return False

		except OSError:
			return False

	return True

def torrentinfo(path):
	e = lt.bdecode(open(path, 'rb').read())
	info = lt.torrent_info(e)
	rval = {
		'path': path,
		'files': [],
	}

	for file in info.files():
		rval['files'].append({
			'filename': file.path.decode('utf8', 'ignore'),
			'size': file.size,
		})

	return rval


def findtorrents(path):
	torrents = []

	for root, sub, files in os.walk(path):
		for file in files:
			if file.endswith('.torrent'):
				torrents.append(torrentinfo(os.path.join(root, file)))

	return torrents

if len(sys.argv) < 3:
	print '%s <torrentpath> <searchpath>' % sys.argv[0]
	sys.exit()


torrents = findtorrents(sys.argv[1])

for root, sub, files in os.walk(sys.argv[2]):
	for torrent in torrents:
		if compare(root, torrent) == True:
			add_torrent(torrent['path'], root)
