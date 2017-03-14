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

function removeEmptyFooterTags() {
  var footerContentElements = document.getElementsByClassName('page-footer-content');

  if (footerContentElements.length > 0) {
    for (var i = footerContentElements.length - 1; i >= 0; i--) {
      var footerContentElement = footerContentElements[i];

      if (footerContentElement.innerHTML.trim() === '') {
        footerContentElement.parentNode.removeChild(footerContentElement);
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

function toggleDisplay(className, on) {
  var elements = document.getElementsByClassName(className);

  if (elements.length > 0) {
    for (var i = 0; i < elements.length; i++) {
      var element = elements[i];
      var previousDisplay = element.style.display;

      if (on !== undefined) {
        element.style.display = on ? 'block' : 'none';
      } else {
        element.style.display =
          (!previousDisplay || previousDisplay == 'block') ?
            'none' :
            'block';
      }
    }

    return elements[0].style.display;
  }
}

function toggleEnability(element, on) {
  element.style.opacity = on ? 1.0 : 0.2;
  element.style.pointerEvents = on ? 'auto' : 'none';
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
  var toggledOn = toggleDisplay('page-backs') == 'block';

  toggleButtons('toggle-card-backs-on', 'toggle-card-backs-off',
    toggledOn);

  // force the two-sided option to follow the backs option (both on and off)
  toggleTwoSided(toggledOn);

  var toggleTwoSidedButton = document.getElementById('toggle-two-sided');

  if (toggleTwoSidedButton) {
    toggleEnability(toggleTwoSidedButton, toggledOn);
  }

  updatePageNumbers();
}

function disableActionsIfNecessary() {
  var pageElements = document.getElementsByClassName('page');

  if (pageElements.length === 0) {
    // no pages generated- disable actions
    var innerToolbarElement = document.getElementById('ui-toolbar-inner');

    if (innerToolbarElement) {
      var actionElements = innerToolbarElement.getElementsByClassName('ui-action');

      for (i = 0; i < actionElements.length; i++) {
        toggleEnability(actionElements[i], false);
      }
    }
  }
}

function toggleTwoSided(on) {
  toggleButtons('toggle-two-sided-on', 'toggle-two-sided-off',
    (toggleDisplay('filler', on) == 'block'));

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

function elementHasClass(element, cls) {
  if (element) {
    return element.className.split(" ").indexOf(cls) != -1;
  }

  return false;
}

function updatePageNumbers() {
  var pageElements = document.getElementsByClassName('page');

  var totalPageCount = 0;
  var totalCardCount = 0;

  if (pageElements.length > 0) {
    var visiblePageElements = [];

    for (var i = 0; i < pageElements.length; i++) {
      var pageElement = pageElements[i];

      if (pageElement.style.display != 'none') {
        visiblePageElements.push(pageElement);
      }
    }

    if (visiblePageElements.length > 0) {
      totalPageCount = visiblePageElements.length;

      for (i = 0; i < visiblePageElements.length; i++) {
        var visiblePageElement = visiblePageElements[i];
        var pageNumberElements = visiblePageElement.getElementsByClassName('page-number-tag');

        if (!elementHasClass(visiblePageElement, "page-backs")) {
          // pages with backs do not count towards total card count
          var cardElements = visiblePageElement.getElementsByClassName('card');

          if (cardElements.length > 0) {
            totalCardCount += cardElements.length;
          }
        }

        if (pageNumberElements.length > 0) {
          var pageNumberElement = pageNumberElements[0];

          // this is assuming that the order of the array is always equal to the order in the DOM
          pageNumberElement.innerHTML = 'Page ' + (i + 1) + ' / ' + totalPageCount;
        }
      }
    }
  }

  var statsElement = document.getElementById('ui-stats');

  if (statsElement) {
    var cardsStat = '' + totalCardCount + ' cards';
    var pagesStat = '' + totalPageCount + ' pages';

    var cardsAndPagesContent = cardsStat + '<br />' + pagesStat;

    statsElement.innerHTML = cardsAndPagesContent;
  }
}

function determineBacksToggleVisibility() {
  var backsPageElements = document.getElementsByClassName('page-backs');

  var containsBacksPages = backsPageElements.length > 0;

  if (!containsBacksPages) {
    var toggleBacksElement = document.getElementById('toggle-card-backs');
    var toggleTwoSidedElement = document.getElementById('toggle-two-sided');

    if (toggleBacksElement) {
      toggleBacksElement.style.display = 'none';
    }

    if (toggleTwoSidedElement) {
      toggleTwoSidedElement.style.display = 'none';
    }
  }
}

function revealUI() {
  var toolbar = document.getElementById('toolbar');

  if (toolbar) {
    toolbar.className = 'ui-toolbar ui-toolbar-revealed do-not-print';
  }
}

window.onload = function() {
  disableActionsIfNecessary();
  determineBacksToggleVisibility();
  toggleTwoSided();
  updatePageNumbers();
  removeOverlappingCutGuides();
  removeEmptyFooterTags();

  setTimeout(function() {
    // assuming the toolbar is hidden by default, we'll do all the DOM modifications we need to
    // and then wait a while before revealing it fully- this prevents any potential flickering
    // while we determine e.g. whether or not to show a backs toggle
    revealUI();
  }, 500);
};
