$(function () {
    "use strict";

    function setParentId($select) {
        var parentId = $select.siblings(".form-parent").val(),
            input = $select.siblings(":hidden[name$='-parent']");
        if ($.isNumeric($select.val())) {
            input.val(parentId);
        } else {
            input.val("");
        }
    }

    var form = $("#pricing-plans"),
        inputSubmit = form.find("input[name=submit]");

    form
        .find(":submit").click(function () {
        inputSubmit.val($(this).data('type'));
    })
        .filter(".delete").click(function () {
        $(this).siblings("[name$='-DELETE']").prop('checked', true);
    });
    form.find("[name$='-person']").change(function () {
        setParentId($(this));
    });

    // autocomplete
    form.find("select[name$=person]").each(function () {
        var $select = $(this),
            $input = $select.siblings("input.autocomplete"),
            source = jQuery.map($select.find("option"), function (el) {
                return {
                    value: $(el).val(),
                    label: $(el).html()
                };
            }).filter(function (el) {
                return !!el.value;
            });
        $input.autocomplete({
            minLength: 0,
            source: function (term, response_cb) {
                var search = term.term.toLowerCase();
                response_cb(source.filter(function (el) {
                    return el.value == search || el.label.toLowerCase().indexOf(search) > -1;
                }));
            },
            focus: function (event, ui) {
                $input.val(ui.item.label);
                return false;
            },
            select: function (event, ui) {
                var options = $select.find("option");
                options.removeAttr("selected");
                options.filter("[value=" + ui.item.value + "]").attr("selected", "selected");
                $input.val(ui.item.label);
                setParentId($select);
                return false;
            }
        });
    });
});
