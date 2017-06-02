
from covertutils.crypto.keys import StandardCyclingKey
from covertutils.crypto.algorithms import StandardCyclingAlgorithm

from covertutils.datamanipulation import AdHocChunker

from covertutils.datamanipulation import Chunker
from covertutils.datamanipulation import Compressor

from covertutils.orchestration import StreamIdentifier
from covertutils.orchestration import Orchestrator

from covertutils.datamanipulation import StegoInjector, DataTransformer

from string import ascii_letters

from os import urandom

from covertutils.helpers import copydoc

def _dummy_function( data, encode = False ) :
	return data



class StegoOrchestrator ( Orchestrator ) :
	"""
The `StegoOrchestrator` class combines compression, chunking, encryption, stream tagging and steganography injection, by utilizing the below `covertutils` classes:

 - :class:`covertutils.datamanipulation.Chunker`
 - :class:`covertutils.datamanipulation.Compressor`
 - :class:`covertutils.crypto.keys.StandardCyclingKey`
 - :class:`covertutils.orchestration.StreamIdentifier`
 - :class:`covertutils.datamanipulation.StegoInjector`
 - :class:`covertutils.datamanipulation.DataTransformer`


	"""

	def __init__( self, passphrase, stego_config, main_template, transformation_list = [], tag_length = 2, cycling_algorithm = None, streams = ['main'], intermediate_function = _dummy_function, reverse = False ) :
		"""
:param str stego_config: The configuration that is passed to :class:`covertutils.datamanipulation.stegoinjector.StegoInjector`.
:param str main_template: The default template that will be used in :func:`readyMessage()` `template` argument.
:param list transformation_list: The Transformation List that is passed to the :class:`covertutils.datamanipulation.datatransformer.DataTransformer` object.
:param func intermediate_function: A *codec* function with signature `codec( data, encode = False )`. The function is called before and injection of a chunk with *encode = True* and after the extraction of a chunk with *encode = False*.
		"""
		self.intermediate_function = intermediate_function
		self.stego_injector = StegoInjector( stego_config )
		self.data_tranformer = DataTransformer( stego_config, transformation_list )
		self.compressor = Compressor()

		self.cycling_algorithm = cycling_algorithm
		if self.cycling_algorithm == None:
			self.cycling_algorithm = StandardCyclingAlgorithm

		self.main_template = main_template
		self.current_template = main_template
		# streams = self.stego_injector.getTemplates()

		super( StegoOrchestrator, self ).__init__( passphrase, tag_length, cycling_algorithm, streams, reverse )

		for index, template in enumerate( self.stego_injector.getTemplates() ) :
			stego_capacity = self.stego_injector.getCapacity( template )
			# print stego_capacity
			inter_product = self.intermediate_function( "0" * stego_capacity, False )	# Need a valid decodable data string "0000..." is valid hex, base64, etc
			intermediate_cap = len( inter_product )	 - self.tag_length # check the capacity of the data length after the intermediate function

			# self.streams_buckets[ template ]['chunker'] = AdHocChunker()


	def useTemplate( self, template ) :
		self.current_template = template


	def lastReceivedTemplate( self ) :
		return self.received_template


	@copydoc(Orchestrator.readyMessage)
	def readyMessage( self, message, stream = None ) :

		template = self.current_template
		if stream == None :
			stream = self.default_stream

		template_capacity = self.stego_injector.getCapacity( template )
		self.streams_buckets[ stream ]['chunker'].setChunkSize( template_capacity )
		chunks = super( StegoOrchestrator, self ).readyMessage( message, stream )

		ready_chunks = []
		for chunk in chunks :
			modified_chunk = self.intermediate_function( chunk, True )
			injected = self.stego_injector.inject( modified_chunk, template )
			alterations = self.getAlterations( template )
			transformed = injected
			for alteration_templ in alterations :
				transformed = self.data_tranformer.runAll( transformed, alteration_templ )	# needs to be documented

			ready_chunks.append( transformed )
		return ready_chunks


	def getAlterations( self, template ) :
		templates = self.stego_injector.getTemplates()
		ret = []
		for templ in templates :
			if templ.startswith( template+"_alt" ) :
				ret.append( templ )
		return ret


	@copydoc(Orchestrator.depositChunk)
	def depositChunk( self, chunk ) :

		templ = self.stego_injector.guessTemplate( chunk )[0]
		self.received_template = templ
		extr_data = self.stego_injector.extract( chunk, templ )
		chunk = self.intermediate_function( extr_data, False )

		ret = super( StegoOrchestrator, self ).depositChunk( chunk )
		return ret


	def addStream( self, stream ) :
		super( StegoOrchestrator, self ).addStream( stream )
		self.streams_buckets[ stream ]['chunker'] = AdHocChunker()
