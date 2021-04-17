/*
* This script make #search-result-wrapper switch to unloaded or shown automatically.
*/



(function(document) {

  const btnSearchTrigger = document.getElementById("search-trigger");
  const sidebarTrigger = document.getElementById("sidebar-trigger");
  const btnCancel = document.getElementById("search-cancel");
  const btnClear = document.getElementById("search-cleaner");

  const main = document.getElementById("main-content");
  const navbar = document.getElementById("navbar");
  const searchWrapper = document.getElementById("search-wrapper");
  const resultWrapper = document.getElementById("search-result-wrapper");
  const results = document.getElementById("search-results");
  const input = document.getElementById("search-input");

  const scrollBlocker = (function () {
    let offset = 0;
    return {
      block() {
        offset = window.scrollY;
        document.documentElement.scrollTop = 0;
      },
      release() {
        document.documentElement.scrollTop = offset;
      },
      getOffset() {
        return offset;
      }
    };
  }());


  /*--- Actions in small screens (Sidebar unloaded) ---*/

  const mobileSearchBar = (function () {
    return {
      on() {
        btnSearchTrigger.classList.add("unloaded");
        sidebarTrigger.classList.add("unloaded");
        searchWrapper.classList.add("d-flex");
        searchWrapper.classList.add("w-95");
        navbar.classList.add("d-flex");
        btnCancel.classList.add("loaded");
      },
      off() {
        btnSearchTrigger.classList.remove("unloaded");
        sidebarTrigger.classList.remove("unloaded");
        searchWrapper.classList.remove("d-flex");
        searchWrapper.classList.remove("w-95");
        navbar.classList.remove("d-flex");
        btnCancel.classList.remove("loaded");
      }
    };
  }());

  const resultSwitch = (function () {
    let visible = false;

    return {
      on() {
        if (!visible) {
          // the block method must be called before $(#main) unloaded.
          scrollBlocker.block();
          resultWrapper.classList.remove("unloaded");
          main.classList.add("unloaded");
          visible = true;
        }
      },
      off() {
        if (visible) {
          results.innerHTML = "";
          resultWrapper.classList.add("unloaded");
          btnClear.classList.remove("visible");
          main.classList.remove("unloaded");

          // now the release method must be called after $(#main) display
          scrollBlocker.release();

          input.value = "";
          visible = false;
        }
      },
      isVisible() {
        return visible;
      }
    };

  }());

  function isMobileView() {
    return btnCancel.classList.contains("loaded");
  }

  btnSearchTrigger.addEventListener('click', e => {
    mobileSearchBar.on();
    resultSwitch.on();
    input.focus();
  });

  btnCancel.addEventListener('click', e => {
    mobileSearchBar.off();
    resultSwitch.off();
  });
  
  input.addEventListener('focus', e => {
    searchWrapper.classList.add("input-focus");
  })

  input.addEventListener('blur', e => {
    searchWrapper.classList.remove("input-focus");
  })

  input.addEventListener('keyup', e => {
    if (e.keyCode === 8 && input.value === "") {
      if (!isMobileView()) {
        resultSwitch.off();
      }
    } else {
      if (input.value !== "") {
        resultSwitch.on();
  
        if (!btnClear.classList.contains("visible")) {
          btnClear.classList.add("visible");
        }
      }
    }
  })

  btnClear.addEventListener("click", function() {
    input.value = "";
    if (isMobileView()) {
      results.innerHTML = "";
    } else {
      resultSwitch.off();
    }
    input.focus();
    btnClear.classList.remove("visible");
  });

  function onResize() {
    if (window.getComputedStyle(btnSearchTrigger, null).display != 'none') {
      if (window.innerWidth <= 475 && location.pathname != '/') {
        btnSearchTrigger.classList.add('hidden');
      } else {
        btnSearchTrigger.classList.remove('hidden');
      }
    }
  }

  window.addEventListener('resize', onResize, false);
  onResize();

})(document);
