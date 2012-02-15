$(function () {
    $("div.dialog a.close").click(function (e) {
        e.preventDefault();
        $("div.dialog").fadeOut("fast");
        $("input.url").val("");
    });
    var uploadComplete = function (url) {
        insertAtCaret("description", "![](" + url + ")");
        $(".dialog-image").fadeOut("fast");
    };
    $(".dialog").removeClass("do-hide");
    $(".dialog-image").hide();
    $(".dialog-link").hide();
    $(".dialog-link button").click(function (e) {
        e.preventDefault();
        if ($(".dialog-link input.url").val() == "") {
            $(".dialog-link p.hint").removeClass("noerror");
            $(".dialog-link p.hint").text("You didn't enter a URL");
            $(".dialog-link input.url").focus().select();
            return false;
        }
        if ($("input.url").val() != "" && $("input.url").val().substr(0, 7) != "http://" &&
                $("input.url").val().substr(0, 8) != "https://") {
            $("input.url").val("http://" + $("input.url").val())
        }
        if ($("input.url")[0].checkValidity()) {
            var title = $("input.link-name").val() || $("input.url").val();
            insertAtCaret("description", "[" + title + "](" + $(".dialog-link input.url").val() + ")");
            $("div.dialog").fadeOut("fast");
            $("input.url").val("");
        } else {
            $(".dialog-link p.hint").removeClass("noerror");
            $(".dialog-link p.hint").css({"opacity": 0.1});
            $(".dialog-link p.hint").text("This doesn't seem to be a valid URL");
            $(".dialog-link input.url").focus().select();
            $(".dialog-link p.hint").animate({"opacity": 1}, "fast");
        }
    });
    $(".dialog-image p.hint").attr("orig-text", $(".dialog-image p.hint").text());
    $(".dialog-link p.hint").attr("orig-text", $(".dialog-link p.hint").text());
    $("iframe.upload").load(function () {
        if ($(this).hasClass("loaded")) {
            try {
                var url = JSON.parse($($(this)[0].contentWindow.document).find("pre").text());
                $(".dialog-image p.hint").removeClass("noerror");
                $(".dialog-image iframe").hide();
                if (url == 404) {
                    $("p.hint").text("You didn't select a file yet.");
                } else if (url == 405) {
                    $("p.hint").text("");
                } else if (url == 401) {
                    $("p.hint").text("You are not authenticated correctly.");
                } else if (url == 413) {
                    $("p.hint").text("Sorry, this file is too large.");
                } else if (url == 415) {
                    $("p.hint").text("Sorry, this file type isn't supported.");
                } else if (url == 500) {
                    $("p.hint").text("Sorry, there was an error.");
                } else {
                    uploadComplete(url);
                    $(this).removeClass("loaded");
                    $("iframe.upload")[0].contentWindow.location.href = "/img_upload";
                    return false;
                }
                $(this).removeClass("loaded");
                $("iframe.upload")[0].contentWindow.location.href = "/img_upload";
            } catch (e) {
                $("p.hint").text("Sorry, we can't read this file.");
                $(this).removeClass("loaded");
                $("iframe.upload")[0].contentWindow.location.href = "/img_upload";
            };
        } else {
            $(this).addClass("loaded");
            $(".dialog-image iframe").show();
        }
    });
    $(".more").removeAttr("style");
    $(".more").hide();
    $("a.show-more").click(function (e) {
        e.preventDefault();
        $(".markdown-help .more").slideDown("fast");
        $(".markdown-help .simple").slideUp("fast");
    });
    $("a.show-less").click(function (e) {
        e.preventDefault();
        $(".markdown-help .simple").slideDown("fast");
        $(".markdown-help .more").slideUp("fast");
        $("body").scrollTop($(".markdown-help").position().top - 100);
    });
    function insertAtCaret(areaId,text) {
        /* with thanks to Stack Overflow user 'gclaghorn' */
        var txtarea = document.getElementById(areaId);
        var scrollPos = txtarea.scrollTop;
        var strPos = 0;
        var br = ((txtarea.selectionStart || txtarea.selectionStart == '0') ? 
            "ff" : (document.selection ? "ie" : false ) );
        if (br == "ie") { 
            txtarea.focus();
            var range = document.selection.createRange();
            range.moveStart ('character', -txtarea.value.length);
            strPos = range.text.length;
        }
        else if (br == "ff") strPos = txtarea.selectionStart;

        var front = (txtarea.value).substring(0,strPos);  
        var back = (txtarea.value).substring(strPos,txtarea.value.length); 
        txtarea.value=front+text+back;
        strPos = strPos + text.length;
        if (br == "ie") { 
            txtarea.focus();
            var range = document.selection.createRange();
            range.moveStart ('character', -txtarea.value.length);
            range.moveStart ('character', strPos);
            range.moveEnd ('character', 0);
            range.select();
        }
        else if (br == "ff") {
            txtarea.selectionStart = strPos;
            txtarea.selectionEnd = strPos;
            txtarea.focus();
        }
        txtarea.scrollTop = scrollPos;
    }
    var textSub = function (pre, post, example, code) {
        var len = $("textarea.md").val().length;
        var start = $("textarea.md")[0].selectionStart;
        var end = $("textarea.md")[0].selectionEnd;
        var selectedText = $("textarea.md").val().substring(start, end);

        if (selectedText == "") {
            insertAtCaret("description", example);
        } else if (code == true) {
            $("textarea.md").val(function () {
                    var codeAlready = true;
                    var tx = selectedText.split("\n")
                    if (tx.length == 1) {
                        return $(this).val().substring(0, this.selectionStart) +
                        "`" + selectedText + "`" + $(this).val().substring(this.selectionEnd);
                    } else {
                        for (var i = 0; i < tx.length; i++) {
                            if (tx[i].substring(0, 4) != "    ") codeAlready = false;
                        }
                        if (codeAlready == true) {
                            var newText = "";
                            for (var i = 0; i < tx.length; i++) {
                                newText += tx[i].substr(4) + "\n";
                            }
                        } else {
                            var newText = "    " + tx.join("\n    ");
                        }
                        return $(this).val().substring(0, this.selectionStart) +
                            newText + $(this).val().substring(this.selectionEnd);
                    }
            });
        } else {
            $("textarea.md").val(function () {
                    return $(this).val().substring(0, this.selectionStart) +
                        pre + selectedText + post + $(this).val().substring(this.selectionEnd);
                });
        }
    };
    $("a[href=#md-bold]").click(function (e) {
        e.preventDefault(); textSub("**", "**", "**bold**");
    });
    $("a[href=#md-italics]").click(function (e) {
        e.preventDefault(); textSub("_", "_", "_italics_");
    });
    $("a[href=#md-img]").click(function (e) {
        var len = $("textarea.md").val().length;
        var start = $("textarea.md")[0].selectionStart;
        var end = $("textarea.md")[0].selectionEnd;
        var selectedText = $("textarea.md").val().substring(start, end);
        $(".dialog-image p.hint").text($(".dialog-image p.hint").attr("orig-text"));
        $(".dialog-image p.hint").addClass("noerror");
        $(".dialog-image").fadeIn("fast");
        e.preventDefault();
    });
    $("a[href=#md-link]").click(function (e) {
        var len = $("textarea.md").val().length;
        var start = $("textarea.md")[0].selectionStart;
        var end = $("textarea.md")[0].selectionEnd;
        var selectedText = $("textarea.md").val().substring(start, end);
        $(".dialog-link p.hint").text($(".dialog-link p.hint").attr("orig-text"));
        $(".dialog-link p.hint").addClass("noerror");
        $("input.url").val("");
        $("input.link-name").val("");
        if ((selectedText.length > 1) && (selectedText.substr(0, 7) == "http://")) {
            textSub("<" + selectedText, ">", "");
        } else {
            $(".dialog-link").fadeIn("fast");
        }
        e.preventDefault();
    });
    $("a[href=#md-pre]").click(function (e) {
        e.preventDefault(); textSub("", "", "\n    code is indented by four spaces", true);
    });
    $("aside.md-hint.hint").hide();
    $("a.mdx").hover(function () {
            $("aside.md-hint.hint").text($(this).attr("data-hint") || "no").fadeIn(1000);
    });
    $("div.markdown-help").hover(function () {}, function () {
        $("aside.md-hint.hint").text("").hide();
    });
});
