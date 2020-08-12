# Django core
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q
from django.core.serializers import serialize
from django.http import JsonResponse
from django.db import connection
from django.views.decorators.cache import cache_page
from django.contrib.gis.geos import GEOSGeometry

# Other Python modules
import json 
from datetime import datetime
from psycopg2 import sql

# Third Party Django apps
from constance import config

# Memory Map Toolkit
from .models import Point, Line, Polygon, Theme, Document, Image, AudioFile
from mmt_pages.models import Page
from mmt_api.serializers import PointSerializer, PolygonSerializer, PointDetailSerializer, DocumentSerializer
from .vector_tile_helpers import tileIsValid, tileToEnvelope


def index(request):
	"""Base map"""

	themes = Theme.objects.all()
	pages = Page.objects.all().order_by('order')

	return render(request, 'mmt_map/index.html', {'themes': themes})


def feature_detail(request, pk, source_layer):
	"""Get info about a single feature"""

	if source_layer == 'points':
		feature = get_object_or_404(Point, id=pk)
		documents = Document.objects.filter(point=feature)
		images = Image.objects.filter(point=feature)
		audio = AudioFile.objects.filter(point=feature)
	elif source_layer == 'polygons':
		feature = get_object_or_404(Polygon, id=pk)
		documents = Document.objects.filter(polygon=feature)
		images = Image.objects.filter(polygon=feature)
		audio = AudioFile.objects.filter(polygon=feature)
	elif source_layer == 'lines':
		feature = get_object_or_404(Line, id=pk)
		documents = Document.objects.filter(line=feature)
		images = Image.objects.filter(line=feature)
		audio = AudioFile.objects.filter(line=feature)

	attachments_base = {'documents': documents, 'images': images, 'audio': audio}

	attachments = []
	for key, value in attachments_base.items():
		for v in value:
			attachments.append(v)
	
	attachments = sorted(attachments, key=lambda attachment: attachment.order)

	host = request.get_host()

	today = datetime.today()

	return render(request, 'mmt_map/feature.html', {'feature': feature, 'attachments': attachments, 'host': host, 'today': today })


def text_only_feature_list(request):
	"""A text only representation of features to provide access to memory map content for blind and partially-sighted users"""

	themes = Theme.objects.all()

	return render(request, 'mmt_map/feature_list.html', {'themes': themes})


# Vector tiles are optionally cached to stop the database being spammed to heavily.
@cache_page(60 * config.CACHE_TIMEOUT)
def vector_tile(request, z, x, y, tile_format):
	"""
	Returns a vector tile. Uses raw SQL because GeoDjango can't return vector tiles (though to my mind it should). Tiles are optionally cached so as to make large maps more performant, at the expense of updates not being visible immediately. Adapted from https://github.com/pramsey/minimal-mvt, though refactored so the query is built without using string.format()!
	"""
	tile = {
		'zoom': int(z),
		'x': int(x),
		'y': int(y),
		'format': tile_format
	}

	if not tileIsValid(tile):
		return HttpResponse('<p>Tile request not valid</p>', status=400)

	env = tileToEnvelope(tile)

	DENSIFY_FACTOR = 4
	env['segSize'] = (env['xmax'] - env['xmin'])/DENSIFY_FACTOR

	# The query has to be built manually to return the geometries as vector tiles. Must be changed if you update the models

	sql_tmpl = """
		WITH 
		"bounds" AS (
			SELECT ST_Segmentize(ST_MakeEnvelope(%(xmin)s, %(ymin)s, %(xmax)s, %(ymax)s, 3857),%(segSize)s) AS "geom", 
				   ST_Segmentize(ST_MakeEnvelope(%(xmin)s, %(ymin)s, %(xmax)s, %(ymax)s, 3857),%(segSize)s)::box2d AS "b2d"
		),
		"mvtgeom" AS (
			SELECT ST_AsMVTGeom(ST_Transform("t"."geom", 3857), "bounds"."b2d") AS "geom", 
				   "id", "name", "weight", "theme_id", "tag_str"
			FROM  {table} "t", "bounds"
			WHERE ST_Intersects("t"."geom", ST_Transform("bounds"."geom", 4326)) AND "published" = TRUE
		) 
		SELECT ST_AsMVT("mvtgeom".*, {layerName}) FROM "mvtgeom"
	"""

	# Map the geometry types to PostGIS database tables and layer names for consumption by MapboxGL

	layers = {
		'points': {
			'table': 'mmt_map_point',
			'layerName': "points"
		},
		'polygons': {
			'table': 'mmt_map_polygon',
			'layerName': "polygons"
		},
		'lines': {
			'table': 'mmt_map_line',
			'layerName': "lines"
		}
	}

	# Build the HttpResponse

	response = HttpResponse()
	response['Access-Control-Allow-Origin'] = '*'
	response['Content-type'] = 'application/vnd.mapbox-vector-tile'

	# Loop over the layers and concatenate them into the response

	for layer, attrs in layers.items():

		query = sql.SQL(sql_tmpl).format(table=sql.Identifier(attrs['table']), layerName=sql.Literal(attrs['layerName']))

		params = {'xmin': env['xmin'], 'ymin': env['ymin'], 'xmax': env['xmax'], 'ymax': env['ymax'], 'segSize': env['segSize']}

		with connection.cursor() as cursor:
			cursor.execute(query, params)
			pbf = cursor.fetchone()[0]
	
		response.write(pbf.tobytes())
	
	# Return the tile

	return response


def tile_json(request):
	"""Returns a tileJSON object describing the vector tiles hosted in the Memory Map toolkit database."""
	
	scheme = request.scheme
	host = request.get_host()

	json = {
		'tileJSON': '2.2.0',
		'name': 'Memory Map Toolkit Interactive Features',
		'tiles': [
			scheme + '://' + host + '/tiles/{z}/{x}/{y}.pbf'
		],
	}

	return JsonResponse(json)
