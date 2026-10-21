"""
Backtest Agent - Evaluates past AI predictions against actual market movements.
Refactored to use BaseAgent and fix JSON serialization issues.
"""
import json
import os
from datetime import datetime
from agents.base_agent import BaseAgent

class BacktestAgent(BaseAgent):
    def __init__(self, model_router=None, vector_db=None):
        super().__init__('BacktestAgent', model_router, vector_db)
        self.history_file = 'data/reports/backtest_history.json'
        os.makedirs('data/reports', exist_ok=True)

    def execute(self, sentiment_data=None, market_data=None):
        """
        Evaluate past predictions against current market data.
        """
        self.log("Evaluating past predictions...")
        
        # 1. Load existing history
        history = self._load_history()
        
        # 2. Evaluate new predictions (if data is provided)
        if sentiment_data and market_data:
            new_predictions = self._generate_predictions(sentiment_data, market_data)
            history.extend(new_predictions)
            self.log(f"Added {len(new_predictions)} new predictions to history.")

        # 3. Evaluate historical predictions (simulate 24h+ check)
        evaluated_history = self._evaluate_history(history)
        
        # 4. Save updated history safely
        self._save_history(evaluated_history)

        # 5. Calculate final stats for the dashboard
        stats = self._calculate_stats(evaluated_history)
        
        self.log(f"Accuracy: {stats['accuracy_pct']}% ({stats['total_wins']}/{stats['total_evaluated']})", 'SUCCESS')
        return stats

    def _load_history(self):
        """Load prediction history from disk."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.log(f"Could not load history file: {e}", 'WARN')
        return []

    def _save_history(self, history):
        """Save prediction history to disk. 
        FIX: Uses default=str to handle numpy booleans and datetime objects."""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                # default=str is the critical fix for the "bool is not JSON serializable" error
                json.dump(history, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            self.log(f"Could not save backtest database: {e}", 'ERROR')

    def _generate_predictions(self, sentiment_data, market_data):
        """
        Generate new predictions based on current sentiment.
        (In a full production system, this would map specific asset sentiments to specific tickers).
        """
        predictions = []
        overall_sentiment = sentiment_data.get('overall_sentiment', 0)
        overall_label = sentiment_data.get('overall_label', 'Neutral')
        
        # Example: Predicting overall market direction based on overall sentiment
        if overall_label != 'Neutral':
            prediction = {
                'date': datetime.now().isoformat(),
                'asset': 'Overall Market',
                'ai_prediction': 'UP' if overall_sentiment > 0 else 'DOWN',
                'ai_confidence': abs(overall_sentiment) / 100.0,
                'actual_move': None, # Will be filled in future runs
                'is_correct': None,
                'status': 'pending'
            }
            predictions.append(prediction)
            
        return predictions

    def _evaluate_history(self, history):
        """
        Check pending predictions against actual market moves.
        """
        evaluated_count = 0
        for pred in history:
            if pred.get('status') == 'pending' and pred.get('actual_move') is not None:
                actual_move = float(pred['actual_move'])
                ai_pred = pred.get('ai_prediction', '')
                
                # Simple evaluation logic
                if ai_pred == 'UP' and actual_move > 0:
                    pred['is_correct'] = True
                elif ai_pred == 'DOWN' and actual_move < 0:
                    pred['is_correct'] = True
                else:
                    pred['is_correct'] = False
                    
                pred['status'] = 'evaluated'
                evaluated_count += 1
                
        if evaluated_count > 0:
            self.log(f"Evaluated {evaluated_count} past prediction cycles.")
        return history

    def _calculate_stats(self, history):
        """Calculate accuracy metrics for the dashboard."""
        evaluated = [p for p in history if p.get('status') == 'evaluated']
        total_evaluated = len(evaluated)
        
        if total_evaluated == 0:
            return {
                'total_evaluated': 0,
                'total_wins': 0,
                'accuracy_pct': 0.0,
                'recent_results': []
            }

        # Count wins (ensure we handle boolean types safely)
        total_wins = sum(1 for p in evaluated if p.get('is_correct') == True)
        accuracy_pct = (total_wins / total_evaluated) * 100 if total_evaluated > 0 else 0.0

        # Get recent results for the UI (last 10)
        recent_results = evaluated[-10:]
        
        # Clean up recent results for UI display
        clean_recent = []
        for r in recent_results:
            clean_recent.append({
                'date': r.get('date', '')[:10],
                'asset': r.get('asset', 'Unknown'),
                'ai_label': r.get('ai_prediction', 'N/A'),
                'market_move': float(r.get('actual_move', 0)),
                'is_correct': bool(r.get('is_correct', False)) # Force native Python bool
            })

        return {
            'total_evaluated': total_evaluated,
            'total_wins': total_wins,
            'accuracy_pct': round(accuracy_pct, 1),
            'recent_results': clean_recent
        }