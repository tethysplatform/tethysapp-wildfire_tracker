from tethys_sdk.base import TethysAppBase
from tethys_sdk.app_settings import CustomSetting


class WildfireVisualizer(TethysAppBase):
    """
    Tethys app class for Wildfire Visualizer.
    """
    name = 'Wildfire Visualizer'
    description = ''
    package = 'wildfire_visualizer'  # WARNING: Do not change this value
    index = 'home'
    icon = f'{package}/images/wildfire-icon.png'
    root_url = 'wildfire-visualizer'
    color = '#c23616'
    tags = ''
    enable_feedback = False
    feedback_emails = []

    def custom_settings(self):
        custom_settings = (
            CustomSetting(
                name='FIRMS_api_token',
                type=CustomSetting.TYPE_STRING,
                required=True
            ),
        )

        return custom_settings
