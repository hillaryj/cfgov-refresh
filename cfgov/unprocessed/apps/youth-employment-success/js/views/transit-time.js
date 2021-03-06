import { checkDom, setInitFlag } from '../../../../js/modules/util/atomic-helpers';
import {
  updateTimeToActionPlan,
  updateTransitTimeHoursAction,
  updateTransitTimeMinutesAction
} from '../reducers/route-option-reducer';
import inputView from './input';

const CLASSES = Object.freeze( {
  CONTAINER: 'm-yes-transit-time'
} );

const NOT_SURE_MESSAGE = 'Looking up how long this trip takes was added to your to-do list.';

/**
 * TransitTimeView
 * @class
 *
 * @classdesc Initializes the organism.
 *
 * @param {HTMLNode} element The root DOM element for this view
 * @param {object} props Additional properties to be supplied to the view
 * @returns {Object} The view's public methods
 */
function transitTimeView( element, { store, routeIndex, todoNotification } ) {
  const _dom = checkDom( element, CLASSES.CONTAINER );
  const _inputs = Array.prototype.slice.call(
    _dom.querySelectorAll( 'input' )
  );
  const _actionMap = {
    timeToActionPlan: updateTimeToActionPlan,
    transitTimeHours: updateTransitTimeHoursAction,
    transitTimeMinutes: updateTransitTimeMinutesAction
  };

  /**
   * Updates form state from child input text nodes
   * @param {object} updateObject object with DOM event and field name
   */
  function _setResponse( { name, event } ) {
    const method = _actionMap[name];
    const type = event.target.type;
    const value = type === 'checkbox' ? event.target.checked : event.target.value;

    if ( type === 'checkbox' ) {
      if ( value ) {
        todoNotification.show( NOT_SURE_MESSAGE );
      } else {
        todoNotification.hide();
      }
    }

    if ( method ) {
      store.dispatch( method( {
        routeIndex, value } ) );
    }
  }

  /**
   * Initialize the input elements this form manages
   */
  function _initInputs() {
    _inputs.forEach( input => {
      inputView( input, {
        events: {
          input: _setResponse
        },
        type: input.type === 'checkbox' ? 'checkbox' : 'text'
      } ).init();
    } );
  }

  return {
    init() {
      if ( setInitFlag( _dom ) ) {
        _initInputs();
        todoNotification.init( _dom );
      }
    }
  };
}

transitTimeView.CLASSES = CLASSES;

export default transitTimeView;
