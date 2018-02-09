// Enable bootstrap confirmation plugin
$('[data-toggle=popover]').popover();
$('[data-toggle="confirmation"]').confirmation();
$('#nodes-table').on('all.bs.table', function (e, name, args) {
    $('[data-toggle="confirmation"]').confirmation();
});

$(function() {
    // Populate launch instance popover
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
        var row = $('[name="launchConfigGroup"]:checked').parents('tr');
        var type_elem = $(row.children()[2]);
        var instance_type = type_elem.text();
        window.location.replace('/observatory/add_node?instance_type=' + instance_type);
    });

    $(document).delegate('.btn-cancel-option', 'click', function(e) {
        e.preventDefault();
        var element = $(this).parents('.popover');
        if(element.size()){
            $(element).removeClass('in').addClass('out');
        }
    });
});

