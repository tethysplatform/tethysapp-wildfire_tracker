var map;
let currentLayer;

var $updateForm;


$(document).ready(function () {
    map = TETHYS_MAP_VIEW.getMap();


    $updateForm = $('#update-form');
    $updateForm.on('submit', function (event) {
        event.preventDefault();
        let formData = new FormData(this);

        formData.append('method', 'update_map');
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
            if (data.geojson.features.length == 0) {
                TETHYS_APP_BASE.alert("danger", "No data found for the selected parameters.", "danger");
            } else {
                let newPointSource = new ol.source.Vector();
                data.geojson.features.forEach((point) => {
                    let coords = ol.proj.fromLonLat([point.geometry.coordinates[0], point.geometry.coordinates[1]]);
                    let feature = new ol.Feature({
                        geometry: new ol.geom.Point(coords),
                    })

                    feature.setStyle(new ol.style.Style({
                        image: new ol.style.Circle({
                            radius: 6,
                            fill: new ol.style.Fill({
                                color: 'red'
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
            }
        });
    })
});
