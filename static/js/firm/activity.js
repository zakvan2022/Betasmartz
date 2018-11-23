(function () {
    "use strict";

    function handlePeriodChange() {
        var elem = this;
        if (elem.value === "custom") {
            $("#ytdPicker").hide();
            $("#customDatepicker").show();
        } else if (elem.value === "ytd") {
            $("#customDatepicker").hide();
            $("#ytdPicker").show();
        } else {
            $("#customDatepicker").hide();
            $("#ytdPicker").hide();
            $("#id_ytd").remove();
            $("#id_start").remove();
            $("#id_end").remove();
            elem.form.submit();
        }
    }

    $(function () {
        $("#ytdPicker").find("input").datepicker({
            endDate: "0d",
            orientation: "top"
        }).on("changeDate", function (e) {
            $("#id_start").remove();
            $("#id_end").remove();
            $("#activityFilterForm").submit();
        });
        $("#customDatepicker").find(".input-daterange").datepicker({
            endDate: "0d",
            orientation: "top"
        }).on("changeDate", function (e) {
            $("#id_ytd").remove();
            $("#activityFilterForm").submit();
        });
        $("#id_period").change(handlePeriodChange);
    });
    betasmartz.widgets.searchTable("#activity", null, {
      saveState: true
  });
}());
