# -*- coding: utf-8 -*-
#from sampy import *
#from SocketServer import ThreadingMixIn
try:
	import sampy
except ImportError:
	import astropy.vo.samp as sampy
import logging
import threading
import time
import astropy.vo.samp

logger = logging.getLogger("vaex.samp")


class Samp(object):
	def __init__(self, daemon=True, name=None):
		self.client = sampy.SAMPIntegratedClient(metadata = {"samp.name":"Gavi client" if name is None else name,
										"samp.description.text": "Gavi client" if name is None else name,
										"gavi.samp.version":"0.01"}, callable=True)


		# sampy doesn't make this thread Daeamon, so the python process never stops on the cmd line
		# this fixes that
		def _myrun_client():
			if self.client.client._callable:
				self.client.client._thread = threading.Thread(target = self.client.client._serve_forever)
				self.client.client._thread.setDaemon(True)
				self.client.client._thread.start()
		if daemon:
			self.client.client._run_client = _myrun_client
		connected = False
		try:
			self.client.connect()
			connected = True
		except sampy.SAMPHubError as e:
			#print "error connecting to hub", e
			pass

		if connected:
			#self.client.client._thread.setDaemon(False)
			logger.info("connected to SAMP hub")
			logger.info("binding events")
			self.client.bindReceiveCall			("table.load.votable", self._onTableLoadVotable)
			self.client.bindReceiveNotification	("table.load.votable", self._onTableLoadVotable)
			#self.client.bindReceiveNotification	("table.highlight.row", self._onSampNotification)
			#self.client.bindReceiveMessage("table.load.votable", self._onSampCall)
			#self.client.bindReceiveResponse("table.load.votable", self._onSampCall)
			
			#self.client.bindReceiveCall("samp.*", self._onSampCall)
			#self.client.bindReceiveNotification("samp.*", self._onSampNotification)
			
			#self.client.bindReceiveCall("table.*", self._onSampCall)
			#self.client.bindReceiveNotification("table.*", self._onSampNotification)
			#self.client.bindReceiveMessage("table.*", self._onSampCall)
			#self.client.bindReceiveResponse("table.*", self._onSampCall)
			
			#self.client.bindReceiveMessage("table.votable.*", self._onSampCall)
			#self.client.bindReceiveResponse("table.votable.*", self._onSampCall)
			
	#def connect(self):
	#	self.client.connect()
		self.tableLoadCallbacks = []
	
	def _onTableLoadVotable(self, private_key, sender_id, msg_id, mtype, params, extra):
		print(("Msg:", repr(private_key), repr(sender_id), repr(msg_id), repr(mtype), repr(params), repr(extra)))
		try:
			url = params["url"]
			table_id = params["table-id"]
			name = params["name"]
			for callback in self.tableLoadCallbacks:
				callback(url, table_id, name)
		except:
			logger.exception("event handler failed")
		
		if msg_id != None: # if SAMP call, send a reply
			self.client.ereply(msg_id, sampy.SAMP_STATUS_OK, result = {"txt": "loaded"})
		
	def _onSampNotification(self, private_key, sender_id, mtype, params, extra):
		print(("Notification:", repr(private_key), repr(sender_id), repr(mtype), repr(params), repr(extra)))
		
	def _onSampCall(self, private_key, sender_id, msg_id, mtype, params, extra):
		print("----")
		try:
			print(("Call:", repr(private_key), repr(sender_id), repr(msg_id), repr(mtype), repr(params), repr(extra)))
			self.client.ereply(msg_id, sampy.SAMP_STATUS_OK, result = {"txt": "printed"})
		except:
			print("errrrrrrororrrr hans!")



# similar to http://astrofrog-debug.readthedocs.io/en/latest/vo/samp/example_table_image.html
class SampSingle(object):
	def __init__(self, name="vaex - single table load"):
		self.done = False
		self.client = astropy.vo.samp.SAMPIntegratedClient(name=name)
		self.client.connect()

		def call(private_key, sender_id, msg_id, mtype, params, extra):
			self.params = params
			self.client.reply(msg_id, {"samp.status": "samp.ok", "samp.result": {}})
			self.done = True
		def notify(private_key, sender_id, mtype, params, extra):
			self.params = params
			self.done = True

		self.client.bind_receive_call("table.load.votable", call)
		self.client.bind_receive_notification("table.load.votable", notify)



	def wait_for_table(self):
		logging.debug("waiting for samp msg: table.load.votable")
		while not self.done:
			time.sleep(0.1)
		logging.debug("got samp msg: table.load.votable with params: %s", self.params)
		self.client.disconnect()
		return self.params["url"]