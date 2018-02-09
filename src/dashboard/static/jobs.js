// Enable bootstrap confirmation plugin
$('[data-toggle="popover"]').popover();
$('[data-toggle="confirmation"]').confirmation();
$('#jobs-table').on('all.bs.table', function (e, name, args) {
    $('[data-toggle="confirmation"]').confirmation();
});
