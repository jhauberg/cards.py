function removeOverlappingCutGuides() {
  var elements = document.getElementsByClassName('cut-guide');

  if (elements.length > 0) {
    for (var i = 0; i < elements.length; i++) {
      var element = elements[i];
      var elementFrame = element.getBoundingClientRect();

      for (var j = 0; j < elements.length; j++) {
        if (i == j) {
          continue;
        }

        var otherElement = elements[j];
        var otherElementFrame = otherElement.getBoundingClientRect();

        var overlap = !(elementFrame.right < otherElementFrame.left ||
                        elementFrame.left > otherElementFrame.right ||
                        elementFrame.bottom < otherElementFrame.top ||
                        elementFrame.top > otherElementFrame.bottom);

        if (overlap) {
          otherElement.parentNode.removeChild(otherElement);
        }
      }
    }
  }
}

function toggleVisibility(className) {
  var elements = document.getElementsByClassName(className);

  if (elements.length > 0) {
    for (var i = 0; i < elements.length; i++) {
      var element = elements[i];
      var previousVisibility = element.style.visibility;

      element.style.visibility =
        (!previousVisibility || previousVisibility == 'visible') ?
          'hidden' :
          'visible';
    }

    return elements[0].style.visibility;
  }
}

function toggleDisplay(className) {
  var elements = document.getElementsByClassName(className);

  if (elements.length > 0) {
    for (var i = 0; i < elements.length; i++) {
      var element = elements[i];
      var previousDisplay = element.style.display;

      element.style.display =
        (!previousDisplay || previousDisplay == 'block') ?
          'none' :
          'block';
    }

    return elements[0].style.display;
  }
}

function toggleButtons(buttonOn, buttonOff, on) {
  var toggleButtonOn = document.getElementById(buttonOn);
  var toggleButtonOff = document.getElementById(buttonOff);

  toggleButtonOn.style.display = on ? 'inline' : 'none';
  toggleButtonOff.style.display = on ? 'none' : 'inline';
}

function toggleFooter() {
  toggleButtons('toggle-footer-on', 'toggle-footer-off',
    (toggleVisibility('page-footer') == 'visible'));
}

function toggleCutGuides() {
  toggleButtons('toggle-cut-guides-on', 'toggle-cut-guides-off',
    (toggleVisibility('cut-guide') == 'visible'));
}

function toggleCardBacks() {
  toggleButtons('toggle-card-backs-on', 'toggle-card-backs-off',
    (toggleDisplay('page-backs') == 'block'));

  updatePageNumbers();
}

function toggleHelp(on) {
  var modal = document.getElementById('ui-modal-help');

  if (modal) {
    modal.style.display = on ? 'block' : 'none';

    if (on) {
      window.onclick = function(event) {
        if (event.target == modal) {
          toggleHelp(false);
        }
      };
    } else {
      window.onclick = null;
    }
  }
}

function updatePageNumbers() {
  var pageElements = document.getElementsByClassName('page');

  if (pageElements.length > 0) {
    var visiblePageElements = [];

    for (var i = 0; i < pageElements.length; i++) {
      var pageElement = pageElements[i];

      if (pageElement.style.display != 'none') {
        visiblePageElements.push(pageElement);
      }
    }

    if (visiblePageElements.length > 0) {
      var totalPageCount = visiblePageElements.length;

      for (i = 0; i < visiblePageElements.length; i++) {
        var visiblePageElement = visiblePageElements[i];
        var pageNumberElements = visiblePageElement.getElementsByClassName('page-number-tag');

        if (pageNumberElements.length > 0) {
          var pageNumberElement = pageNumberElements[0];

          // this is assuming that the order of the array is always equal to the order in the DOM
          pageNumberElement.innerHTML = 'Page ' + (i + 1) + ' / ' + totalPageCount;
        }
      }
    }
  }
}

window.onload = function() {
  updatePageNumbers();
  removeOverlappingCutGuides();
};
