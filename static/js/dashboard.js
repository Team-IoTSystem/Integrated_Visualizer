// デモ用ダミーデータ取得サーバ
// 描画用設定
API_ROOT = 'https://www.hyperlocalcontext.com/';
DEFAULT_SOCKET_URL = API_ROOT;
WHEREIS_TRANSMITTER_ROOT = API_ROOT + '/whereis/transmitter/';
WHATAT_RECEIVER_ROOT = API_ROOT + '/whatat/receiver/';
CONTEXTAT_DIRECTORY_ROOT = API_ROOT + '/contextat/directory/';
DEFAULT_DIRECTORY_ID = 'Unspecified';
DEFAULT_UPDATE_MILLISECONDS = 1000;
DEFAULT_BEAVER_OPTIONS = {
    disappearanceMilliseconds: 60000,
    mergeEvents: true,
    mergeEventProperties: ['receiverId', 'receiverDirectory', 'rssi',
        'passedFilters'],
    maintainDirectories: true
};
LINE_CHART_SAMPLES = 8;
LINE_CHART_SERIES = ['Devices', 'Displacements'];
LINE_CHART_OPTIONS = {
    legend: {
        display: true,
        position: 'left'
    },
    scales: {
        xAxes: [{
            type: 'linear',
            position: 'bottom'
        }]
    }
};
BAR_CHART_LABELS = ['Max RSSI', 'Avg RSSI', 'Min RSSI'];
BAR_CHART_OPTIONS = {};
DOUGHNUT_CHART_SAMPLES = 8;
DOUGHNUT_CHART_OPTIONS = {};
CHART_COLORS = ['#00bcd4', '#4caf50', '#ff9800', '#f44336',
    '#e91e63', '#82b6cf', '#a9a9a9', '#5a5a5a'];

// Angularモジュール設定
angular.module('dashboard', ['chart.js', 'ui.bootstrap', 'reelyactive.beaver',
    'reelyactive.cormorant'])

    .controller('DashCtrl', function ($scope, $interval, beaver, cormorant) {

        // Variables accessible in the HTML scope
        $scope.elapsedSeconds = 0;
        $scope.devices = [];
        $scope.directories = [];
        $scope.cumStats = beaver.getStats();
        $scope.curStats = {
            appearances: 0, keepalives: 0,
            displacements: 0, disappearances: 0,
            passedFilters: 0, failedFilters: 0
        };
        $scope.rssi = {};
        $scope.stories = [];
        $scope.linechart = {
            labels: [], series: LINE_CHART_SERIES, data: [[], []],
            options: LINE_CHART_OPTIONS
        };
        $scope.barchart = {labels: BAR_CHART_LABELS, data: [], options: {}};
        $scope.doughnutchart = {labels: [], data: [], options: {}};
        $scope.chartColors = CHART_COLORS;

        // Variables accessible in the local scope
        var socket = io.connect(DEFAULT_SOCKET_URL);
        var updateSeconds = DEFAULT_UPDATE_MILLISECONDS / 1000;
        var devices = beaver.getDevices();
        var directories = beaver.getDirectories();
        var stories = cormorant.getStories();
        var storyStats = {};
        var rssi = {min: 255, max: 0, sum: 0, count: 0};
        var appearances = 0;
        var keepalives = 0;
        var displacements = 0;
        var disappearances = 0;
        var passedFilters = 0;
        var failedFilters = 0;

        // beaver.js listens on the websocket for events
        beaver.listen(socket, DEFAULT_BEAVER_OPTIONS);

        // Handle events pre-processed by beaver.js
        beaver.on('appearance', function (event) {
            appearances++;
            handleEvent('appearance', event);
        });
        beaver.on('displacement', function (event) {
            displacements++;
            handleEvent('displacement', event);
        });
        beaver.on('keep-alive', function (event) {
            keepalives++;
            handleEvent('keep-alive', event);
        });
        beaver.on('disappearance', function (event) {
            disappearances++;
            handleEvent('disappearance', event);
        });

        // Handle an event
        function handleEvent(type, event) {
            if (event.passedFilters) {
                passedFilters++;
            }
            else {
                failedFilters++;
            }
            cormorant.getStory(event.deviceUrl, function () {
                cormorant.getStory(event.receiverUrl, function () {
                });
            });
        }

        // Sample the current state of all detected devices
        function sampleDevices() {
            var devicesArray = [];

            for (id in devices) {
                var device = devices[id];
                device.url = WHEREIS_TRANSMITTER_ROOT + id;
                device.receiverUrl = WHATAT_RECEIVER_ROOT + device.event.receiverId;
                devicesArray.push(device);
                addStoryStat(device.event.deviceUrl);
                updateRssiStats(device.event.rssi);
            }

            $scope.devices = devicesArray;
        }

        // Sample the current state of the directories
        function sampleDirectories() {
            var directoryArray = [];

            for (id in directories) {
                var directory = directories[id];
                directory.filteredCount = 0;
                if (id !== 'null') {
                    directory.id = id;
                    directory.url = CONTEXTAT_DIRECTORY_ROOT + id;
                }
                else {
                    directory.id = DEFAULT_DIRECTORY_ID;
                }
                for (device in directory.devices) {
                    if (directory.devices[device].event.passedFilters) {
                        directory.filteredCount++;
                    }
                }
                directory.receiverCount = Object.keys(directory.receivers).length;
                directory.deviceCount = Object.keys(directory.devices).length;
                directoryArray.push(directory);
            }

            $scope.directories = directoryArray;
        }

        // Sample the stats from the previous period
        function sampleStats() {
            var stats = {
                appearances: appearances,
                keepalives: keepalives,
                displacements: displacements,
                disappearances: disappearances,
                passedFilters: passedFilters,
                failedFilters: failedFilters
            };
            appearances = 0;
            keepalives = 0;
            displacements = 0;
            disappearances = 0;
            passedFilters = 0;
            failedFilters = 0;

            $scope.curStats = stats;
        }

        // Sample the RSSI from the previous period
        function sampleRssi() {
            var rssiSample = {};
            if (rssi.count > 0) {
                rssiSample = {
                    min: rssi.min,
                    max: rssi.max,
                    avg: Math.round(rssi.sum / rssi.count),
                    count: rssi.count
                };
            }
            rssi = {min: 255, max: 0, sum: 0, count: 0};

            $scope.rssi = rssiSample;
        }

        // Update the line chart
        function updateLineChart() {
            $scope.linechart.data[0].push({
                x: $scope.elapsedSeconds,
                y: $scope.devices.length
            });
            $scope.linechart.data[1].push({
                x: $scope.elapsedSeconds,
                y: $scope.curStats.displacements
            });
            if ($scope.linechart.data[0].length > LINE_CHART_SAMPLES) {
                $scope.linechart.data[0].shift();
                $scope.linechart.data[1].shift();
            }
        }

        // Update the bar chart
        function updateBarChart() {
            $scope.barchart.data = [$scope.rssi.max, $scope.rssi.avg, $scope.rssi.min];
        }

        // Update the doughnut chart
        function updateDoughnutChart() {
            var labels = [];
            var data = [];
            var storyStatsArray = Object.values(storyStats);
            var sampleLimit = Math.min(storyStatsArray.length, DOUGHNUT_CHART_SAMPLES);
            var cStory = 0;
            var otherCount = 0;

            function compare(a, b) {
                if (a.count < b.count) return 1;
                if (a.count > b.count) return -1;
                return 0;
            }

            storyStatsArray.sort(compare);

            for (cStory = 0; cStory < (sampleLimit - 1); cStory++) {
                labels.push(storyStatsArray[cStory].type);
                data.push(storyStatsArray[cStory].count);
            }
            while (cStory < storyStatsArray.length) {
                otherCount += storyStatsArray[cStory++].count;
            }
            labels.push('All others');
            data.push(otherCount);

            $scope.stories = storyStatsArray.slice(0, sampleLimit - 1);
            $scope.stories.push({type: 'All others', count: otherCount});

            $scope.doughnutchart.labels = labels;
            $scope.doughnutchart.data = data;

        }

        // Add the given story URL to the statistics
        function addStoryStat(url) {
            if (storyStats.hasOwnProperty(url)) {
                storyStats[url].count++;
            }
            else {
                var type = url;
                if (type.indexOf('Organization') >= 0) {
                    type = type.substr(type.indexOf('Organization'));
                }
                else if (type.indexOf('Product') >= 0) {
                    type = type.substr(type.indexOf('Product'));
                }
                storyStats[url] = {type: type, count: 1, url: url};
            }
        }

        // Add the device RSSI to the statistics
        function updateRssiStats(deviceRssi) {
            if (deviceRssi < rssi.min) {
                rssi.min = deviceRssi;
            }
            else if (deviceRssi > rssi.max) {
                rssi.max = deviceRssi;
            }
            rssi.sum += deviceRssi;
            rssi.count++;
        }

        // Periodic update of display variables
        function periodicUpdate() {
            $scope.elapsedSeconds += updateSeconds;
            storyStats = {};
            sampleDevices();
            sampleDirectories();
            sampleStats();
            sampleRssi();
            updateLineChart();
            updateBarChart();
            updateDoughnutChart();
        }

        // Update the update period
        $scope.updatePeriod = function (period) {
            if (period) {
                updateSeconds = period / 1000;
                $scope.updateMessage = "Updating every " + updateSeconds + "s";
                $interval.cancel($scope.updatePromise);
                $scope.updatePromise = $interval(periodicUpdate, period);
                periodicUpdate();
            }
            else {
                $scope.updateMessage = "Updates paused";
                $interval.cancel($scope.updatePromise);
            }
        };

        $scope.updatePeriod(DEFAULT_UPDATE_MILLISECONDS);
    });

// 画面処理
(function () {
    isWindows = navigator.platform.indexOf('Win') > -1 ? true : false;

    if (isWindows) {
        // if we are on windows OS we activate the perfectScrollbar function
        $('.sidebar .sidebar-wrapper, .main-panel').perfectScrollbar();

        $('html').addClass('perfect-scrollbar-on');
    } else {
        $('html').addClass('perfect-scrollbar-off');
    }
})();


var searchVisible = 0;
var transparent = true;

var transparentDemo = true;
var fixedTop = false;

var mobile_menu_visible = 0,
    mobile_menu_initialized = false,
    toggle_initialized = false,
    bootstrap_nav_initialized = false;

var seq = 0,
    delays = 80,
    durations = 500;
var seq2 = 0,
    delays2 = 80,
    durations2 = 500;


$(document).ready(function () {

    $sidebar = $('.sidebar');

    $.material.init();

    window_width = $(window).width();

    md.initSidebarsCheck();

    // check if there is an image set for the sidebar's background
    md.checkSidebarImage();

    //  Activate the tooltips
    $('[rel="tooltip"]').tooltip();

    $('.form-control').on("focus", function () {
        $(this).parent('.input-group').addClass("input-group-focus");
    }).on("blur", function () {
        $(this).parent(".input-group").removeClass("input-group-focus");
    });

});

$(document).on('click', '.navbar-toggle', function () {
    $toggle = $(this);

    if (mobile_menu_visible == 1) {
        $('html').removeClass('nav-open');

        $('.close-layer').remove();
        setTimeout(function () {
            $toggle.removeClass('toggled');
        }, 400);

        mobile_menu_visible = 0;
    } else {
        setTimeout(function () {
            $toggle.addClass('toggled');
        }, 430);

        div = '<div id="bodyClick"></div>';
        $(div).appendTo('body').click(function () {
            $('html').removeClass('nav-open');
            mobile_menu_visible = 0;
            setTimeout(function () {
                $toggle.removeClass('toggled');
                $('#bodyClick').remove();
            }, 550);
        });

        $('html').addClass('nav-open');
        mobile_menu_visible = 1;

    }
});

// リサイズ時の画面処理
$(window).resize(function () {
    md.initSidebarsCheck();
    seq = seq2 = 0;
});

md = {
    misc: {
        navbar_menu_visible: 0,
        active_collapse: true,
        disabled_collapse_init: 0,
    },

    checkSidebarImage: function () {
        $sidebar = $('.sidebar');
        image_src = $sidebar.data('image');

        if (image_src !== undefined) {
            sidebar_container = '<div class="sidebar-background" style="background-image: url(' + image_src + ') "/>'
            $sidebar.append(sidebar_container);
        }
    },

    checkScrollForTransparentNavbar: debounce(function () {
        if ($(document).scrollTop() > 260) {
            if (transparent) {
                transparent = false;
                $('.navbar-color-on-scroll').removeClass('navbar-transparent');
            }
        } else {
            if (!transparent) {
                transparent = true;
                $('.navbar-color-on-scroll').addClass('navbar-transparent');
            }
        }
    }, 17),

    initSidebarsCheck: function () {
        if ($(window).width() <= 991) {
            if ($sidebar.length != 0) {
                md.initRightMenu();
            }
        }
    },

    initRightMenu: debounce(function () {
        $sidebar_wrapper = $('.sidebar-wrapper');

        if (!mobile_menu_initialized) {
            $navbar = $('nav').find('.navbar-collapse').children('.navbar-nav.navbar-right');

            mobile_menu_content = '';

            nav_content = $navbar.html();

            nav_content = '<ul class="nav nav-mobile-menu">' + nav_content + '</ul>';

            navbar_form = $('nav').find('.navbar-form').get(0).outerHTML;

            $sidebar_nav = $sidebar_wrapper.find(' > .nav');

            // insert the navbar form before the sidebar list
            $nav_content = $(nav_content);
            $navbar_form = $(navbar_form);
            $nav_content.insertBefore($sidebar_nav);
            $navbar_form.insertBefore($nav_content);

            $(".sidebar-wrapper .dropdown .dropdown-menu > li > a").click(function (event) {
                event.stopPropagation();

            });

            // simulate resize so all the charts/maps will be redrawn
            window.dispatchEvent(new Event('resize'));

            mobile_menu_initialized = true;
        } else {
            if ($(window).width() > 991) {
                // reset all the additions that we made for the sidebar wrapper only if the screen is bigger than 991px
                $sidebar_wrapper.find('.navbar-form').remove();
                $sidebar_wrapper.find('.nav-mobile-menu').remove();

                mobile_menu_initialized = false;
            }
        }
    }, 200),


    startAnimationForLineChart: function (chart) {

        chart.on('draw', function (data) {
            if (data.type === 'line' || data.type === 'area') {
                data.element.animate({
                    d: {
                        begin: 600,
                        dur: 700,
                        from: data.path.clone().scale(1, 0).translate(0, data.chartRect.height()).stringify(),
                        to: data.path.clone().stringify(),
                        easing: Chartist.Svg.Easing.easeOutQuint
                    }
                });
            } else if (data.type === 'point') {
                seq++;
                data.element.animate({
                    opacity: {
                        begin: seq * delays,
                        dur: durations,
                        from: 0,
                        to: 1,
                        easing: 'ease'
                    }
                });
            }
        });

        seq = 0;
    },
    startAnimationForBarChart: function (chart) {

        chart.on('draw', function (data) {
            if (data.type === 'bar') {
                seq2++;
                data.element.animate({
                    opacity: {
                        begin: seq2 * delays2,
                        dur: durations2,
                        from: 0,
                        to: 1,
                        easing: 'ease'
                    }
                });
            }
        });

        seq2 = 0;
    }
}

function debounce(func, wait, immediate) {
    var timeout;
    return function () {
        var context = this,
            args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(function () {
            timeout = null;
            if (!immediate) func.apply(context, args);
        }, wait);
        if (immediate && !timeout) func.apply(context, args);
    };
};