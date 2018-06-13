// Enable bootstrap confirmation plugin
$('[data-toggle=popover]').popover();
$('[data-toggle="confirmation"]').confirmation();
$('#nodes-table').on('all.bs.table', function (e, name, args) {
    $('[data-toggle="confirmation"]').confirmation();
});


function handle_alert_closed(alert_id) {
    $.ajax({
        url: '/observatory/clear_alert?alert_id=' + alert_id,
        type: 'get',
        success: function(response) {
            $('#alerts-container').html(response);
            add_alert_handlers();
        },
        error: function(xhr) {
            console.log('Failed to populate alerts.');
        }
    });
}


function add_alert_handlers() {
    console.log('add_alert_handlers');
    $('.alert').on('closed.bs.alert', function (e) {
        alert_id = $(this).data('alert-id')
        handle_alert_closed(alert_id);
    });
}


$(function() {
    // Populate launch instance popover.
    $.ajax({
        url: '/observatory/launch_popover',
        type: 'get',
        success: function(response) {
            $('#instance-types-table-container').html(response);
            //$('#instance-types-table').bootstrapTable();
            $(window).trigger('ConfigurePopover', {});
        },
        error: function(xhr) {
            console.log('Failed to populate launch panel.')
        }
    });

    // Populate alerts.
    function load_alerts() {
        $.ajax({
            url: '/observatory/nodes_alerts',
            type: 'get',
            success: function(response) {
                $('#alerts-container').html(response);
                add_alert_handlers();
            },
            error: function(xhr) {
                console.log('Failed to populate alerts.')
            }
        });
    }

    load_alerts()
    setTimeout(load_alerts, 30000)
});


$(window).bind('ConfigurePopover', function(e, data) {
    $('#launch-instance-button').popover({
        placement : 'Right',
        title : 'Change',
        trigger : 'click',
        html : true,
        content : function(){
            var content = '';
            content = $('#instance-types-table-container').html();
            return content;
        }
    }).on('shown.bs.popover', function() {
        // Anything to do after popover appears goes here.
    });

    $(document).delegate('.btn-launch','click', function(e) {
        // Launch on-demand instance
        e.preventDefault();
        var config_row = $('[name="launchConfigGroup"]:checked').parents('tr');
        var type_elem = $(config_row.children()[2]);
        var instance_type = type_elem.text();
        // Get zone, if any
        var zone_row = $('[name="zoneGroup"]:checked');
        zone_arg = '';
        if (zone_row.length) {
            var zone_elem = $(zone_row.parents('tr').children()[1]);
            var zone = zone_elem.text();
            zone_arg = '&zone=' + zone;
        }
        window.location.replace('/observatory/add_node?instance_type=' + instance_type + zone_arg);
    });

    $(document).delegate('.btn-spot','click', function(e) {
        // Launch spot instance
        e.preventDefault();
        var config_row = $('[name="launchConfigGroup"]:checked').parents('tr');
        var type_elem = $(config_row.children()[2]);
        var instance_type = type_elem.text();
        // Get zone, if any
        var zone_row = $('[name="zoneGroup"]:checked');
        zone_arg = '';
        if (zone_row.length) {
            var zone_elem = $(zone_row.parents('tr').children()[1]);
            var zone = zone_elem.text();
            zone_arg = '&zone=' + zone;
        }
        window.location.replace('/observatory/add_node?instance_type=' + instance_type + zone_arg + '&spot_bid=True');
    });

    $(document).delegate('.btn-cancel-option', 'click', function(e) {
        e.preventDefault();
        var element = $(this).parents('.popover');
        if(element.size()){
            $(element).removeClass('in').addClass('out');
        }
    });
});
