async function loadAttackData() {

    const response = await fetch("/api/attacks");

    const data = await response.json();


    document.getElementById(
        "source-country-count"
    ).textContent = data.source_country_count;


    document.getElementById(
        "target-country-count"
    ).textContent = data.target_country_count;


    const updatedTime = new Date(data.last_updated);

    document.getElementById(
        "last-updated"
    ).textContent = updatedTime.toLocaleTimeString();


    const attackList =
        document.getElementById("attack-list");

    attackList.innerHTML = "";


    data.attacks.forEach(attack => {

        const attackElement =
            document.createElement("div");

        attackElement.className = "attack-row";


        attackElement.innerHTML = `
            <span>
                #${attack.rank}
            </span>

            <span>
                ${attack.source_country}
            </span>

            <span>
                →
            </span>

            <span>
                ${attack.target_country}
            </span>

            <strong>
                ${attack.percentage}%
            </strong>
        `;


        attackList.appendChild(attackElement);

    });
}


loadAttackData();