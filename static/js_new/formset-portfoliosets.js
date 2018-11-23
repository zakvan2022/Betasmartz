$(function () {
    betasmartz.widgets.searchTable('table.goals', undefined, {
        'initialSorting': [],
        'responsive': true
    });

    $('form.portfolio select').on('change', function (e) {
        var select = $(e.currentTarget),
        submit = select.closest('form.portfolio').find('.show-confirm-modal');
        var $all_selects = select.closest('.goals').find('select');
        var status = false;
        $all_selects.each(function() {
            var item = $(this);
            var initial_value = $('#initial_' + item.attr('id')).data('value');
            if (item.find('option:selected').val() != initial_value) {
                submit.removeClass('hidden');
                status = true;
                return false;
            }
        });
        if (!status) {
            submit.addClass('hidden');
        }
    });

    $('.show-confirm-modal').on('click', function() {
        var form = $(this).closest('form.portfolio');
        $('#confirm_portfolio_changes_modal').data('form', form);
    })

    $('.save-portfolio').on('click', function() {
        $(this).parent().children().attr('disabled', 'disabled');
        $('#confirm_portfolio_changes_modal').data('form').submit();
    })
});
