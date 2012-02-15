    var getSupportInfo = function () {
        // you have found #3 of 100 hidden packages
        var browser = '';
        var browserVersion = 0;
        if (/Opera[\/\s](\d+\.\d+)/.test(navigator.userAgent)) {
            browser = 'Opera';
        } else if (/MSIE (\d+\.\d+);/.test(navigator.userAgent)) {
            browser = 'MSIE';
        } else if (/Navigator[\/\s](\d+\.\d+)/.test(navigator.userAgent)) {
            browser = 'Netscape';
        } else if (/Chrome[\/\s](\d+\.\d+)/.test(navigator.userAgent)) {
            browser = 'Chrome';
        } else if (/Safari[\/\s](\d+\.\d+)/.test(navigator.userAgent)) {
            browser = 'Safari';
            /Version[\/\s](\d+\.\d+)/.test(navigator.userAgent);
            browserVersion = new Number(RegExp.$1);
        } else if (/Firefox[\/\s](\d+\.\d+)/.test(navigator.userAgent)) {
            browser = 'Firefox';
        }
        if(browserVersion === 0){
            browserVersion = RegExp.$1;
        }
        var hasFlash = false;
        for (var i=0; i < navigator.plugins.length; i++) {
            if (navigator.plugins[i].name == "Shockwave Flash") {
                hasFlash = true;
            }
        }
        return {
            browser: browser + " " + browserVersion,
            platform: navigator.platform,
            cookiesEnabled: navigator.cookieEnabled,
            resolution: screen.width + "×" + screen.height,
            windowSize: $(window).width() + "×" + $(window).height(),
            language: navigator.language,
            flashEnabled: hasFlash,
            javaEnabled: navigator.javaEnabled()
        };
    };
$(function () {
    $("aside.banner").hide().removeClass("do-hide");
    if (!(typeof(localStorage) == 'undefined')) {
        if (localStorage.getItem("intro-shown") != "true") {
            localStorage.setItem("intro-shown", "true");
            $("aside.banner").animate({"height": "show", "opacity": "show"}, "fast");
            $("a[href=#close-banner]").click(function (e) {
                e.preventDefault();
                $("aside.banner").animate({"height": "hide"}, "slow");
            });
        }
    }
});
