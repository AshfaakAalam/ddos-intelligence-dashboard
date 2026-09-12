let attackMap;


async function loadAttackData() {

    try {

        const response = await fetch("/api/attacks");

        const data = await response.json();

        console.log(
            "DDoS data updated:",
            data.last_updated
        );


        updateStatistics(data);

        updateAttackList(data.attacks);

        initializeMap(data.attacks);

    }

    catch (error) {

        console.error(
            "Failed to load attack data:",
            error
        );

    }

}


function updateStatistics(data) {

    document.getElementById(
        "source-country-count"
    ).textContent = data.source_country_count;


    document.getElementById(
        "target-country-count"
    ).textContent = data.target_country_count;


    document.getElementById(
        "attack-count"
    ).textContent = data.attacks.length;


    const updatedTime =
        new Date(data.last_updated);


    document.getElementById(
        "last-updated"
    ).textContent =
        updatedTime.toLocaleTimeString();

}


function updateAttackList(attacks) {

    const attackList =
        document.getElementById("attack-list");


    attackList.innerHTML = "";


    attacks.forEach(attack => {

        const row =
            document.createElement("div");


        row.className = "attack-row";


        row.innerHTML = `

            <span class="attack-rank">
                #${attack.rank}
            </span>

            <span class="attack-country">
                ${attack.source_country}
            </span>

            <span class="attack-arrow">
                →
            </span>

            <span class="attack-country">
                ${attack.target_country}
            </span>

            <span class="attack-percentage">
                ${attack.percentage.toFixed(2)}%
            </span>

        `;


        /*
            Click attack row
        */

        row.addEventListener(
            "click",
            function () {

                focusAttack(attack);

            }
        );


        attackList.appendChild(row);

    });

}

function focusAttack(attack) {

    const sourceCoordinates = [

        Number(attack.source_latitude),

        Number(attack.source_longitude)

    ];


    const targetCoordinates = [

        Number(attack.target_latitude),

        Number(attack.target_longitude)

    ];


    /*
        Invalid coordinates
    */

    if (

        !Number.isFinite(sourceCoordinates[0]) ||

        !Number.isFinite(sourceCoordinates[1]) ||

        !Number.isFinite(targetCoordinates[0]) ||

        !Number.isFinite(targetCoordinates[1])

    ) {

        return;

    }


    /*
        Same source and target
    */

    if (

        sourceCoordinates[0] ===
        targetCoordinates[0]

        &&

        sourceCoordinates[1] ===
        targetCoordinates[1]

    ) {

        attackMap.flyTo(
            sourceCoordinates,
            5,
            {
                duration: 1
            }
        );

        return;

    }


    /*
        Calculate attack curve
    */

    const curvePoints =
        createAttackCurve(
            sourceCoordinates,
            targetCoordinates
        );


    /*
        Zoom to the attack
    */

    attackMap.fitBounds(
        curvePoints,
        {
            padding: [80, 80],
            maxZoom: 5,
            duration: 1
        }
    );

}


function initializeMap(attacks) {

    /*
        Remove previous map
    */

    if (attackMap) {

        attackMap.remove();

    }


    /*
        Create Leaflet map
    */

    attackMap = L.map("attack-map").setView(
        [20, 0],
        2
    );


    /*
        OpenStreetMap tiles

        This is the same tile source
        that was working previously.
    */

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            attribution:
                "&copy; OpenStreetMap contributors"
        }
    ).addTo(attackMap);


    const mapBounds = [];


    attacks.forEach(attack => {

        /*
            Convert coordinates to numbers
        */

        const sourceCoordinates = [

            Number(attack.source_latitude),

            Number(attack.source_longitude)

        ];


        const targetCoordinates = [

            Number(attack.target_latitude),

            Number(attack.target_longitude)

        ];


        /*
            Make sure coordinates are valid
        */

        if (

            !Number.isFinite(
                sourceCoordinates[0]
            ) ||

            !Number.isFinite(
                sourceCoordinates[1]
            ) ||

            !Number.isFinite(
                targetCoordinates[0]
            ) ||

            !Number.isFinite(
                targetCoordinates[1]
            )

        ) {

            console.warn(
                "Invalid coordinates:",
                attack
            );

            return;

        }


        /*
            SOURCE MARKER
        */

        L.circleMarker(
            sourceCoordinates,
            {
                radius: 6,

                weight: 2,

                fillOpacity: 0.9
            }
        )
        .addTo(attackMap)
        .bindPopup(`

            <strong>
                Attack Source
            </strong>

            <br><br>

            Country:
            ${attack.source_country}

            <br>

            Code:
            ${attack.source}

        `);


        /*
            TARGET MARKER
        */

        L.circleMarker(
            targetCoordinates,
            {
                radius: 8,

                weight: 2,

                fillOpacity: 0.9
            }
        )
        .addTo(attackMap)
        .bindPopup(`

            <strong>
                Attack Target
            </strong>

            <br><br>

            Country:
            ${attack.target_country}

            <br>

            Code:
            ${attack.target}

        `);


            /*
                Don't draw a line when
                source and target are identical.

                Example:

                US → US
            */

            if (

        sourceCoordinates[0] ===
        targetCoordinates[0]

        &&

        sourceCoordinates[1] ===
        targetCoordinates[1]

    ) {

        L.circle(
            sourceCoordinates,
            {
                radius: 250000,

                weight: 2,

                opacity: 0.8,

                fillOpacity: 0.08
            }
        )
        .addTo(attackMap)
        .bindPopup(`

            <strong>
                ${attack.source_country}
                →
                ${attack.target_country}
            </strong>

            <br><br>

            Attack Share:
            ${attack.percentage.toFixed(2)}%

            <br>

            Rank:
            #${attack.rank}

        `);


        mapBounds.push(
            sourceCoordinates
        );

        return;

    }


        /*
            Create curved attack path
        */

        const curvePoints =
            createAttackCurve(
                sourceCoordinates,
                targetCoordinates
            );


        /*
            Make stronger attacks
            visually thicker.
        */

        const lineWeight =
            Math.max(
                2,
                Math.min(
                    7,
                    attack.percentage / 2
                )
            );


        /*
            ATTACK PATH
        */

        const attackArc = L.polyline(
    curvePoints,
    {
        weight: lineWeight,
        opacity: 0.85,
        color: "#ff3131",
        smoothFactor: 1,
        className: "attack-arc"
    }
)
.addTo(attackMap);


/*
    Arrow showing attack direction
*/

L.polylineDecorator(
    attackArc,
    {
        patterns: [
            {
                offset: "75%",
                repeat: 0,

                symbol: L.Symbol.arrowHead(
                    {
                        pixelSize: 14,

                        polygon: true,

                        pathOptions: {
                            stroke: false,
                            fill: true,
                            fillOpacity: 1,
                            color: "#ff3131"
                        }
                    }
                )
            }
        ]
    }
).addTo(attackMap);


/*
    Popup on attack arc
*/

attackArc.bindPopup(`

    <div class="attack-popup">

        <div class="popup-title">
            DDOS ATTACK
        </div>

        <div class="popup-route">

            ${attack.source_country}

            <span>→</span>

            ${attack.target_country}

        </div>

        <div class="popup-info">

            <div>
                Attack Share
                <strong>
                    ${attack.percentage.toFixed(2)}%
                </strong>
            </div>

            <div>
                Rank
                <strong>
                    #${attack.rank}
                </strong>
            </div>

        </div>

    </div>

`);
        

        /*
            Add coordinates to bounds
        */

        mapBounds.push(
            sourceCoordinates
        );

        mapBounds.push(
            targetCoordinates
        );

    });


    /*
        Automatically zoom to
        all attack locations.
    */

    if (mapBounds.length > 0) {

        attackMap.fitBounds(
            mapBounds,
            {
                padding: [40, 40]
            }
        );

    }

}


/*
    Create a curved path between
    source and target.
*/

function createAttackCurve(
    sourceCoordinates,
    targetCoordinates
) {

    const sourceLatitude =
        sourceCoordinates[0];

    const sourceLongitude =
        sourceCoordinates[1];


    const targetLatitude =
        targetCoordinates[0];

    const targetLongitude =
        targetCoordinates[1];


    /*
        Calculate midpoint
    */

    const middleLatitude =
        (
            sourceLatitude +
            targetLatitude
        ) / 2;


    const middleLongitude =
        (
            sourceLongitude +
            targetLongitude
        ) / 2;


    /*
        Calculate distance
    */

    const latitudeDifference =
        targetLatitude -
        sourceLatitude;


    const longitudeDifference =
        targetLongitude -
        sourceLongitude;


    const distance =
        Math.sqrt(
            Math.pow(
                latitudeDifference,
                2
            )
            +
            Math.pow(
                longitudeDifference,
                2
            )
        );


    /*
        Prevent division by zero
    */

    if (distance === 0) {

        return [
            sourceCoordinates,
            targetCoordinates
        ];

    }


    /*
        Determine curve height
    */

    const curveHeight =
        Math.min(
            distance * 0.25,
            35
        );


    /*
        Perpendicular direction
    */

    const perpendicularLatitude =
        -longitudeDifference /
        distance;


    const perpendicularLongitude =
        latitudeDifference /
        distance;


    /*
        Bezier control point
    */

    const controlPoint = [

        middleLatitude +
        perpendicularLatitude *
        curveHeight,

        middleLongitude +
        perpendicularLongitude *
        curveHeight

    ];


    /*
        Generate curve points
    */

    const curvePoints = [];

    const numberOfPoints = 50;


    for (
        let index = 0;
        index <= numberOfPoints;
        index++
    ) {

        const t =
            index /
            numberOfPoints;


        const oneMinusT =
            1 - t;


        const latitude =

            Math.pow(
                oneMinusT,
                2
            ) *
            sourceLatitude

            +

            2 *
            oneMinusT *
            t *
            controlPoint[0]

            +

            Math.pow(
                t,
                2
            ) *
            targetLatitude;


        const longitude =

            Math.pow(
                oneMinusT,
                2
            ) *
            sourceLongitude

            +

            2 *
            oneMinusT *
            t *
            controlPoint[1]

            +

            Math.pow(
                t,
                2
            ) *
            targetLongitude;


        curvePoints.push([
            latitude,
            longitude
        ]);

    }


    return curvePoints;

}

loadAttackData();

setInterval(
    loadAttackData,
    30 * 1000
);