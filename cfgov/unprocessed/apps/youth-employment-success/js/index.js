import Expandable from 'cf-expandables/src/Expandable';
import { addRouteOptionAction } from './reducers/route-option-reducer';
import budgetFormView from './budget-form-view';
import createRoute from './route.js';
import averageCostView from './views/average-cost';
import daysPerWeekView from './views/days-per-week';
import milesView from './views/miles';
import goalsView from './views/goals';
import reviewGoalsView from './views/review/goals';
import routeOptionFormView from './route-option-view';
import routeOptionToggleView from './add-route-option-view';
import routeDetailsView from './views/route-details';
import expandableView from './views/expandable';
import store from './store';
import transitTimeView from './views/transit-time';

Array.prototype.slice.call(
  document.querySelectorAll( 'input' )
).forEach( input => {
  input.removeAttribute( 'disabled' );
} );

const BUDGET_CLASSES = budgetFormView.CLASSES;
const OPTION_CLASSES = routeOptionFormView.CLASSES;
const OPTION_TOGGLE_CLASSES = routeOptionToggleView.CLASSES;
const GOALS_CLASSES = goalsView.CLASSES;
const REVIEW_GOALS_CLASSES = reviewGoalsView.CLASSES;

// Create factory initializers for all of these view initialize calls, separate files?
const goalsViewEl = document.querySelector( ` .${ GOALS_CLASSES.CONTAINER }` );
const goalsFormView = goalsView( goalsViewEl, { store } );
goalsFormView.init();

const budgetFormEl = document.querySelector( `.${ BUDGET_CLASSES.FORM }` );
const budgetForm = budgetFormView( budgetFormEl, { store } );
budgetForm.init();

reviewGoalsView( document.querySelector( `.${ REVIEW_GOALS_CLASSES.CONTAINER }` ), { store } ).init();

let expandables = [];

function addRouteExpandable( el ) {
  let routeEl = el;

  if ( !routeEl ) {
    const parent = document.querySelector( '.yes-routes-option-clone' );
    const target = parent.querySelector( '.js-route-option' );
    routeEl = target.cloneNode( true );
    document.querySelector( '.js-initial-routes' ).appendChild( routeEl );
  }

  // Initialize a single expandable up-front.
  const newExpandable = Expandable.init( routeEl );
  expandables = expandables.concat( newExpandable );

  const routeIndex = expandables.length - 1;
  const expandable = expandables[expandables.length - 1];
  expandableView( expandable.element, {
    expandable,
    index: routeIndex
  } ).init();

  store.dispatch( addRouteOptionAction( createRoute() ) );

  const routeOptionsEl = expandable.element.querySelector( `.${ OPTION_CLASSES.FORM }` );
  const routeOptionForm = routeOptionFormView( routeOptionsEl, {
    store,
    routeIndex,
    routeDetailsView,
    averageCostView,
    daysPerWeekView,
    milesView,
    transitTimeView
  } );
  routeOptionForm.init();
}

addRouteExpandable(
  document.querySelector( '.js-route-option-1' )
);

routeOptionToggleView(
  document.querySelector( `.${ OPTION_TOGGLE_CLASSES.BUTTON }` ), {
    onAddExpandable: addRouteExpandable
  }
).init();

/* remove the second expandable so we can properly initialize it when
   the add additional route button is clicked. This will still preserve
   the second route option when JS is unavailable */
document.querySelector( '.js-initial-routes' )
  .removeChild(
    document.querySelector( '.js-route-option-2' )
  );
