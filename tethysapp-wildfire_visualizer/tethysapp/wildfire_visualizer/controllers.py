from tethys_sdk.routing import controller
from tethys_sdk.gizmos import Button, SelectInput, DatePicker, TextInput
from tethys_sdk.layouts import MapLayout
from .app import WildfireVisualizer as App
import requests
from django.http import JsonResponse
import pandas as pd
from io import StringIO


def get_color_from_confidence(confidence):
    if pd.isna(confidence):
        return "#cccccc"
    if isinstance(confidence, str):
        confidence = confidence.lower()
        if confidence == "l":
            return "#1f77b4"
        elif confidence == "n":
            return "#ff7f0e" 
        elif confidence == "h":
            return "#d62728"
    elif isinstance(confidence, (int, float)):
        if confidence < 30:
            return "#1f77b4"
        elif confidence < 80:
            return "#ff7f0e"
        else:
            return "#d62728"
    return "#cccccc"

def get_color_from_frp(frp):
    if pd.isna(frp):
        return "#cccccc"
    elif frp < 10:
        return "#a6cee3"
    elif frp < 30:
        return "#1f78b4"
    elif frp < 50:
        return "#fb9a99"
    else:
        return "#e31a1c"

def fetch_api_data(token, date="", satellite='VIIRS_NOAA20_NRT', days='2'):
        
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{token}/{satellite}/world/{days}/{date}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print("Error fetching data:", e)
            return {"type": "FeatureCollection", "features": []}

def convert_api_to_geojson(data, color_code):
    df = pd.read_csv(StringIO(data))
    wildfires = []
    possibilities = set()
    for _, row in df.iterrows():
        wildfire = {
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
            "coordinates": [row.get("longitude"), row.get("latitude")],
        }
        conf = row.get("confidence")
        possibilities.add(wildfire['properties']['confidence'])
        if color_code == 'confidence':
            wildfire['color'] = get_color_from_confidence(row.get("confidence"))
        elif color_code == 'frp':
            wildfire['color'] = get_color_from_frp(row.get("frp"))

        wildfires.append(wildfire)
    print("Possibilities:", possibilities)
    return {
        "wildfires": wildfires
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
                ('VIIRS NOAA-20 (URT+NRT)', 'VIIRS_NOAA20_NRT'),
                ('VIIRS NOAA-21 (URT+NRT)', 'VIIRS_NOAA21_NRT'),
                ('VIIRS S-NPP (URT+NRT)', 'VIIRS_SNPP_NRT'),
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

        color_code = SelectInput(
            display_text='Color Code',
            name='color_code',
            multiple=False,
            options=[
                ('Confidence', 'confidence'),
                ('Fire Radiative Power (FRP)', 'frp'),
            ]
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
        context['color_code'] = color_code
        context['submit_button'] = submit_button
        
        return context

    def update_map(self, request, *args, **kwargs):
        form_data = request.POST

        satellite = form_data.get('satellite')
        days = form_data.get('days')
        date = form_data.get('date')
        color_code = form_data.get('color_code')

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
        
        geojson_data = convert_api_to_geojson(raw_data, color_code)

        return JsonResponse({
            'geojson': geojson_data,
            'satellite': satellite,
            'days': days,
            'date': date
        }, status=200)
