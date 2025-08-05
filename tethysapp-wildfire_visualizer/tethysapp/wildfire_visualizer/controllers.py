from tethys_sdk.routing import controller
from tethys_sdk.gizmos import Button, SelectInput, DatePicker, TextInput
from tethys_sdk.layouts import MapLayout
from .app import WildfireVisualizer as App
import requests
from django.http import JsonResponse
import pandas as pd
from io import StringIO

def format_wildfire_metadata(data):
    metadata = {}
    if data.get("acq_date") is not None:
        metadata["Acquisition Date"] = data.get("acq_date")
    if data.get("acq_time") is not None:
        acq_time = str(data.get("acq_time"))
        acq_time = acq_time[: -2] + ":" + acq_time[-2:]
        metadata["Acquisition Time"] = acq_time
    if data.get("satellite") is not None:
        metadata["Satellite"] = data.get("satellite")
    if data.get("instrument") is not None:
        metadata["Instrument"] = data.get("instrument")
    if data.get("confidence") is not None:
        if isinstance(data.get("confidence"), str):
            confidence = str(data.get("confidence")).lower()
            if confidence == "l":
                metadata["Confidence"] = "Low"
            elif confidence == "n":
                metadata["Confidence"] = "Nominal"
            elif confidence == "h":
                metadata["Confidence"] = "High"
        else:
            confidence = data.get("confidence")
            metadata["Confidence"] = confidence           
    if data.get("frp") is not None:
        metadata["Fire Radiative Power (FRP)"] = data.get("frp")
    if data.get("bright_ti4") is not None:
        metadata["Brightness Temperatrue I4"] = data.get("bright_ti4")
    if data.get("bright_ti5") is not None:
        metadata["Brightness Temperature I5"] = data.get("bright_ti5")
    if data.get("scan") is not None:
        metadata["Scan"] = data.get("scan")
    if data.get("track") is not None:
        metadata["Track"] = data.get("track")
    if data.get("version") is not None:
        metadata["Version"] = data.get("version")
    if data.get("daynight") is not None:
        if data.get("daynight").lower() == "d":
            metadata["Day/Night"] = "Day"
        elif data.get("daynight").lower() == "n":
            metadata["Day/Night"] = "Night"

    return metadata

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
        return "#33a02c"
    elif frp < 30:
        return "#1f77b4"
    elif frp < 50:
        return "#ff7f0e"
    else:
        return "#d62728"

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
    
    has_no_data_color = False

    wildfires = []
    for _, row in df.iterrows():
        wildfire = {
            "metadata": format_wildfire_metadata(row),
            "coordinates": [row.get("longitude"), row.get("latitude")],
        }

        if color_code == 'confidence':
            wildfire['color'] = get_color_from_confidence(row.get("confidence"))
            if isinstance(row.get("confidence"), str):
                type_of_confidence = "string"
            else:
                type_of_confidence = "numeric"

        elif color_code == 'frp':
            wildfire['color'] = get_color_from_frp(row.get("frp"))

        wildfires.append(wildfire)
        if wildfire['color'] == "#cccccc":
            has_no_data_color = True

    if wildfires:
        legend_data_options = {
            "confidence": {
                "string": {
                    "Low": "#1f77b4",
                    "Nominal": "#ff7f0e",
                    "High": "#d62728"
                },
                "numeric": {
                    "<30": "#1f77b4",
                    "<80": "#ff7f0e",
                    ">=80": "#d62728"
                }
            }, 
            "frp": {
                "<10": "#33a02c",
                "<30": "#1f77b4",
                "<50": "#ff7f0e",
                ">=50": "#d62728"
            }
        }

        if color_code == "confidence":
            legend_data = legend_data_options[color_code][type_of_confidence]
        else:
            legend_data = legend_data_options[color_code]

        if has_no_data_color:
            legend_data["N/A"] = "#cccccc"

        legend_title = "Confidence" if color_code == "confidence" else "Fire Radiative Power (FRP)"
        return {"wildfires": wildfires}, {"title": legend_title, "legend_data": legend_data}
    return {"wildfires": []}, {}

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
                ('MODIS (URT+NRT)', 'MODIS_NRT'),
                ('VIIRS NOAA-20 (URT+NRT)', 'VIIRS_NOAA20_NRT'),
                ('VIIRS NOAA-21 (URT+NRT)', 'VIIRS_NOAA21_NRT'),
                ('VIIRS S-NPP (URT+NRT)', 'VIIRS_SNPP_NRT'),
                ('LANDSAT (NRT) [US/Canada Only]', 'LANDSAT_NRT'),
            ]
         )

        days = SelectInput(
            display_text='Days',
            name='days',
            multiple=False,
            options=[(str(i), str(i)) for i in range(1, 11)],
            initial = '3'
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
        
        geojson_data, legend = convert_api_to_geojson(raw_data, color_code)

        return JsonResponse({
            'geojson': geojson_data,
            'legend': legend,
            'satellite': satellite,
            'days': days,
            'date': date
        }, status=200)
