var map;
let currentLayer;

var $updateForm;
var $loadingOverlay;
var $legendDiv;

// Add a legend to the map
function add_legend_map(map) {
    try {
        let legend_element = document.getElementById('legend');
        let control_panel = new ol.control.Control({
            element: legend_element
        });
        map.addControl(control_panel);
    }  
    catch (error) {
        console.error(error);
    }
}

$(document).ready(function () {
    map = TETHYS_MAP_VIEW.getMap();

    add_legend_map(map);

    $updateForm = $('#update-form');
    $loadingOverlay = $("#loading-overlay");

    $updateForm.on('submit', function (event) {
        event.preventDefault();
        let formData = new FormData(this);

        formData.append('method', 'update_map');
        $loadingOverlay.show();

        fetch('.', {
            method: 'POST',
            body: formData
        }).then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'An unkown error occurred');
                });
            }
            return response.json();
        }).then(data => {
            console.log(data);
            if (data.geojson.wildfires.length == 0) {
                TETHYS_APP_BASE.alert("danger", "No data found for the selected parameters.", "danger");
            } else {
                let newPointSource = new ol.source.Vector();
                data.geojson.wildfires.forEach((fire) => {
                    let coords = ol.proj.fromLonLat([fire.coordinates[0], fire.coordinates[1]]);
                    let feature = new ol.Feature({
                        geometry: new ol.geom.Point(coords),
                    })

                    feature.setStyle(new ol.style.Style({
                        image: new ol.style.Circle({
                            radius: 6,
                            fill: new ol.style.Fill({
                                color: fire.color
                            }),
                            stroke: new ol.style.Stroke({
                                color: 'red',
                                width: 2
                            })
                        })
                    }));

                    newPointSource.addFeature(feature);
                });

                if (currentLayer) {
                    map.removeLayer(currentLayer);
                }

                currentLayer = new ol.layer.Vector({
                    source: newPointSource,
                    name: 'data_layer',
                });

                map.addLayer(currentLayer);

                $legendDiv = $('#legend');

                $legendDiv.empty();

                let legendContentHtml = `<table class='table table-striped table-bordered table-condensed'>
                                        <thead><tr><th colspan='2'>${data.legend.title}</th></tr></thead>
                                        <tbody>`;

                for (let [key, value] of Object.entries(data.legend.legend_data)) {
                    legendContentHtml += `<tr>
                                            <td><div style='width: 20px; height: 20px; background-color: ${value}; border-radius: 50%;'></div></td>
                                            <td>${key}</td>
                                            </tr>`;  
                };

                legendContentHtml += "</tbody></table>";

                $legendDiv.html(legendContentHtml);
                $legendDiv.show();
            }
        }).catch(error => {
            console.error(error);
            TETHYS_APP_BASE.alert("danger", error.message);
        }).finally(() => {
            $loadingOverlay.hide();
        })
    })
});
