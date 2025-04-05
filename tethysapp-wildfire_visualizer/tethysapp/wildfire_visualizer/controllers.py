from tethys_sdk.routing import controller
from tethys_sdk.gizmos import Button, SelectInput, DatePicker, TextInput
from tethys_sdk.layouts import MapLayout
from .app import WildfireVisualizer as App
import requests
from django.http import JsonResponse
import pandas as pd
from io import StringIO

def fetch_api_data(token, date="", satellite='VIIRS_NOAA20_NRT', days='2'):
        
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{token}/{satellite}/world/{days}/{date}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print("Error fetching data:", e)
            return {"type": "FeatureCollection", "features": []}

def convert_api_to_geojson(data):
    df = pd.read_csv(StringIO(data))
    features = []
    for _, row in df.iterrows():
        feature = {
            "type": "Feature",
            "properties": {
                "bright_ti4": row.get("bright_ti4"),
                "scan": row.get("scan"),
                "track": row.get("track"),
                "acq_date": row.get("acq_date"),
                "acq_time": row.get("acq_time"),
                "satellite": row.get("satellite"),
                "instrument": row.get("instrument"),
                "confidence": row.get("confidence"),
                "version": row.get("version"),
                "bright_ti5": row.get("bright_ti5"),
                "frp": row.get("frp"),
                "daynight": row.get("daynight")
            },
            "geometry": {
            "type": "Point",
            "coordinates": [row.get("longitude"), row.get("latitude")]
            }
        }
        features.append(feature)
    return {
        "type": "FeatureCollection",
        "features": features
    }

@controller(name='home')
class WildfireVisualizerMap(MapLayout):
    app = App
    base_template = 'wildfire_visualizer/base.html'
    template_name = 'wildfire_visualizer/home.html'
    map_title = 'Wildfire Visualizer'
    show_properties_popup = True
    plot_slide_sheet = True
    show_legends = True

    baseemaps = ['OpenStreetMap', 'ESRI']

    def get_context(self, request, *args, **kwargs):
        satellite = SelectInput(
            display_text='Satellite', 
            name='satellite',
            multiple=False,
            options=[
                ('LANDSAT (NRT) [US/Canada Only]', 'LANDSAT_NRT'),
                ('MODIS (URT+NRT)', 'MODIS_NRT'),
                ('MODIS (SP)', 'MODIS_SP'),
                ('VIIRS NOAA-20 (URT+NRT)', 'VIIRS_NOAA20_NRT'),
                ('VIIRS NOAA-20 (SP)', 'VIIRS_NOAA20_SP'),
                ('VIIRS NOAA-21 (URT+NRT)', 'VIIRS_NOAA21_NRT'),
                ('VIIRS S-NPP (URT+NRT)', 'VIIRS_SNPP_NRT'),
                ('VIIRS S-NPP (SP)', 'VIIRS_SNPP_SP')
            ]
         )

        days = SelectInput(
            display_text='Days',
            name='days',
            multiple=False,
            options=[(str(i), str(i)) for i in range(1, 11)]
        )

        date = DatePicker(
            display_text='Date',
            name='date',
            initial=pd.Timestamp.now().date(),
        )

        submit_button = Button(
            display_text='Submit',
            name='submit',
            attributes={
                'class': 'btn btn-primary',
                'form': 'update-form'
            },
            style='success',
            submit=True
        )

        context = super().get_context(request, *args, **kwargs)
        context['satellite'] = satellite
        context['days'] = days
        context['date'] = date
        context['submit_button'] = submit_button
        
        return context

    def update_map(self, request, *args, **kwargs):
        form_data = request.POST

        satellite = form_data.get('satellite')
        days = form_data.get('days')
        date = form_data.get('date')

        if not satellite:
             return JsonResponse({'error': 'Satellite is required.'}, status=400)
        
        if not date:
             return JsonResponse({'error': 'Date is required'}, status=400)
        
        parsed_date = pd.to_datetime(date).date()
        formatted_date = parsed_date.strftime('%Y-%m-%d')
        
        token = App.get_custom_setting('FIRMS_api_token')

        raw_data = fetch_api_data(token, date=formatted_date, satellite=satellite, days=days)
        
        if 'Error' in raw_data:
            return JsonResponse({'error': 'Error fetching data from API'}, status=500)
        
        geojson_data = convert_api_to_geojson(raw_data)

        return JsonResponse({
            'geojson': geojson_data,
            'satellite': satellite,
            'days': days,
            'date': date
        }, status=200)
