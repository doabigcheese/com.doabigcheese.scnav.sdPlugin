
var Database = require('Database.json');

Container_list = Object.keys(Database["Containers"]);

Planetary_POI_list = {};
Container_list.forEach(function (container_name) {
    Planetary_POI_list[container_name] = Object.keys(Database["Containers"][container_name]["POI"]);
});


planetary_container_select = document.getElementById("planetary_container_select");
planetary_container_select.appendChild(
    new Option("test1", "test1")
);
Container_list.forEach(function (Container_list) {
    planetary_container_select.appendChild(
        new Option(Container_list, Container_list)
    );
});

planetary_target_select = document.getElementById("planetary_target_select");

planetary_container_select.addEventListener('change', function () {
    

    planetary_target_select.options.length = 0;
    Planetary_POI_list[planetary_container_select.value].forEach(function (Planetary_POI) {
        planetary_target_select.appendChild(
            new Option(Planetary_POI, Planetary_POI)
        );
    });
}, false);

