import { combineReducers, createStore } from 'redux';
import budgetReducer from './reducers/budget-reducer';
import routeOptionReducer from './reducers/route-option-reducer';

/**
 * Function to create a new store instance
 * @returns {Object} A redux store
 */
function configureStore() {
  return createStore(rootReducer);
}

// Export configure store to expose non-singleton for testing
export { configureStore };

const rootReducer = combineReducers( {
  budget: budgetReducer,
  routes: routeOptionReducer
} );

export default configureStore();
