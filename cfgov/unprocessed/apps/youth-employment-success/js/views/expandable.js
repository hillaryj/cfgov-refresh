import { checkDom } from '../../../../js/modules/util/atomic-helpers';

const CLASSES = Object.freeze( {
  CONTAINER: 'o-expandable',
  BUTTON: 'o-expandable_target',
  HEADING: 'o-expandable_label'
} );

/**
 * ExpandableView
 * @class
 *
 * @classdesc Wraps an expandable object instance to allow for DOM manipulation within
 * the route-option-form when an expandable is opened or closed
 *
 * @param {HTMLNode} element The root DOM element for this view
 * @param {Object} props Additional properties to be supplied to the view
 * @param {Object} props.expandable The expandable instance this view manages
 * @returns {Object} The view's public methods
 */
function expandableView( element, { expandable, index } ) {
  const _dom = checkDom( element, CLASSES.CONTAINER );
  let initialized = false;
  let detailsEl;

  if ( !expandable ) {
    throw new TypeError( 'An instance of an expandable is a required prop.' );
  }

  /**
   * If the view has been initialized and was previously opened,
   * remove the route details node.
   */
  function _hideRouteDetails() {
    if ( initialized && detailsEl ) {
      _dom.removeChild( detailsEl );
      detailsEl = null;
    }
  }

  /**
   * Append a copy of the route-details html to the closed expandable. Stores a ref to the DOM
   * node for later removal
   */
  function _showRouteDetails() {
    detailsEl = _dom.querySelector( '.yes-route-details' ).cloneNode( true );
    detailsEl.classList.add( 'o-expandable_content' );
    _dom.appendChild( detailsEl );
  }

  return {
    init() {
      if ( !initialized ) {
        // The expandables are initialized in a closed state, so we need to force it to open.
        expandable.element.querySelector( `.${ CLASSES.BUTTON }` ).click();
        expandable.element.querySelector( `.${ CLASSES.HEADING }` ).textContent = `Option ${ index + 1 }`;
        expandable.transition.addEventListener( 'expandBegin', _hideRouteDetails );
        expandable.transition.addEventListener( 'collapseBegin', _showRouteDetails );
        initialized = true;
      }
    }
  };
}

expandableView.CLASSES = CLASSES;

export default expandableView;
