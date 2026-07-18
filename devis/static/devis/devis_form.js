document.addEventListener("DOMContentLoaded", function () {
    const champType = document.querySelector("#id_type_client");
    if (!champType) return;

    function appliquer() {
        const valeur = champType.value;

        document.querySelectorAll("[id^='id_pp_']").forEach(function (input) {
            const bloc = input.closest("div");
            if (bloc) bloc.style.display = (valeur === "PP") ? "" : "none";
        });

        document.querySelectorAll("[id^='id_pm_']").forEach(function (input) {
            const bloc = input.closest("div");
            if (bloc) bloc.style.display = (valeur === "PM") ? "" : "none";
        });

        document.querySelectorAll("[id^='id_dirigeant_']").forEach(function (input) {
            const bloc = input.closest("div");
            if (bloc) bloc.style.display = (valeur === "PM") ? "" : "none";
        });
    }

    appliquer();
    champType.addEventListener("change", appliquer);
});