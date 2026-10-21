"""
Vector Database Module - Provides persistent memory for the finance agent using ChromaDB.
Uses Ollama embeddings (nomic-embed-text) for semantic search.
Stores news, sentiment, market data, analysis, and backtest results for historical context.
"""
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import os
import json
from datetime import datetime, timedelta

class FinanceVectorDB:
    def __init__(self, persist_dir='data/vector_db', embedding_model='nomic-embed-text'):
        """Initialize ChromaDB client with Ollama embeddings"""
        self.persist_dir = persist_dir
        self.embedding_model = embedding_model
        os.makedirs(persist_dir, exist_ok=True)

        # Create Ollama embedding function
        self.ollama_ef = embedding_functions.OllamaEmbeddingFunction(
            url="http://localhost:11434/api/embeddings",
            model_name=self.embedding_model
        )
        
        # Initialize persistent ChromaDB client with Ollama embeddings
        self.client = chromadb.PersistentClient(path=persist_dir)
        
        # Create or get collections with Ollama embeddings
        self.news_collection = self.client.get_or_create_collection(
            name="news_articles",
            embedding_function=self.ollama_ef,
            metadata={"description": "Financial news articles with semantic embeddings"}
        )
        
        self.sentiment_collection = self.client.get_or_create_collection(
            name="sentiment_snapshots",
            embedding_function=self.ollama_ef,
            metadata={"description": "AI sentiment scores over time"}
        )
        
        self.market_collection = self.client.get_or_create_collection(
            name="market_snapshots",
            embedding_function=self.ollama_ef,
            metadata={"description": "Market prices and changes over time"}
        )
        
        self.analysis_collection = self.client.get_or_create_collection(
            name="ai_analysis",
            embedding_function=self.ollama_ef,
            metadata={"description": "AI-generated analysis outputs"}
        )
        
        self.backtest_collection = self.client.get_or_create_collection(
            name="backtest_results",
            embedding_function=self.ollama_ef,
            metadata={"description": "AI prediction accuracy tracking"}
        )
        
        print(f"    🗄️  Vector DB initialized at {persist_dir}")
        print(f"       🧠 Embedding model: {self.embedding_model}")
        print(f"       📰 News: {self.news_collection.count()} documents")
        print(f"       📊 Sentiment: {self.sentiment_collection.count()} documents")
        print(f"       💹 Market: {self.market_collection.count()} documents")
        print(f"       🧠 Analysis: {self.analysis_collection.count()} documents")
        print(f"       🎯 Backtest: {self.backtest_collection.count()} documents")

    def _get_date_int(self, timestamp_str):
        """Convert timestamp to integer YYYYMMDD for safe ChromaDB $gte filtering"""
        try:
            return int(timestamp_str[:10].replace('-', ''))
        except:
            return int(datetime.now().strftime('%Y%m%d'))

    def _format_date_str(self, date_int):
        """Convert integer YYYYMMDD back to YYYY-MM-DD string for display"""
        date_str = str(date_int)
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        return str(date_int)

    def store_news_articles(self, articles, timestamp=None):
        """Store news articles for semantic search"""
        if not articles:
            return 0
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        date_int = self._get_date_int(timestamp)
        date_str = timestamp[:10]
        
        ids = []
        documents = []
        metadatas = []
        
        for i, article in enumerate(articles):
            doc_id = f"news_{date_str}_{i}_{hash(article.get('title', '')) % 10000}"
            
            title = article.get('title', '')
            summary = article.get('summary', '')
            document = f"{title}. {summary}" if summary else title
            
            if not document.strip():
                continue
            
            metadata = {
                'timestamp': timestamp,
                'date': date_int,  # ✅ Use integer for safe $gte filtering
                'type': 'news',
                'region': article.get('region', 'Global'),
                'region_name': article.get('region_name', 'Global'),
                'source': article.get('source', ''),
                'is_translated': article.get('is_translated', False),
                'original_language': article.get('original_language', 'en'),
                'link': article.get('link', '')
            }
            
            ids.append(doc_id)
            documents.append(document)
            metadatas.append(metadata)
        
        if ids:
            batch_size = 100
            for i in range(0, len(ids), batch_size):
                self.news_collection.upsert(
                    ids=ids[i:i + batch_size],
                    documents=documents[i:i + batch_size],
                    metadatas=metadatas[i:i + batch_size]
                )
        
        return len(ids)

    def store_sentiment_snapshot(self, sentiment_data, timestamp=None):
        """Store sentiment scores for trend analysis"""
        if not sentiment_data:
            return
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        date_int = self._get_date_int(timestamp)
        date_str = timestamp[:10]
        doc_id = f"sentiment_{date_str}"
        
        overall = sentiment_data.get('overall_sentiment', 0)
        label = sentiment_data.get('overall_label', 'Neutral')
        
        document_parts = [f"Overall sentiment: {overall:+d} ({label})"]
        
        asset_sentiments = sentiment_data.get('asset_sentiments', {})
        for asset, data in asset_sentiments.items():
            if isinstance(data, dict):
                score = data.get('score', 0)
                asset_label = data.get('label', 'Neutral')
                document_parts.append(f"{asset}: {score:+d} ({asset_label})")
        
        regional_sentiments = sentiment_data.get('regional_sentiments', {})
        for region, data in regional_sentiments.items():
            if isinstance(data, dict):
                score = data.get('score', 0)
                region_label = data.get('label', 'Neutral')
                document_parts.append(f"{region}: {score:+d} ({region_label})")
        
        drivers = sentiment_data.get('key_drivers', [])
        if drivers:
            document_parts.append(f"Key drivers: {', '.join(drivers[:5])}")
        
        document = '. '.join(document_parts)
        
        metadata = {
            'timestamp': timestamp,
            'date': date_int,  # ✅ Use integer
            'type': 'sentiment',
            'overall_score': overall,
            'overall_label': label,
            'shift': sentiment_data.get('sentiment_shift', 'stable')
        }
        
        self.sentiment_collection.upsert(
            ids=[doc_id],
            documents=[document],
            metadatas=[metadata]
        )

    def store_market_snapshot(self, market_data, timestamp=None):
        """Store market prices for historical reference"""
        if not market_data:
            return
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        date_int = self._get_date_int(timestamp)
        date_str = timestamp[:10]
        doc_id = f"market_{date_str}"
        
        document_parts = []
        for category, groups in market_data.items():
            if isinstance(groups, dict):
                for group_name, tickers in groups.items():
                    if isinstance(tickers, list):
                        for ticker in tickers:
                            name = ticker.get('name', '')
                            price = ticker.get('price', 0)
                            change = ticker.get('daily_change', 0)
                            weekly = ticker.get('weekly_change', 0)
                            document_parts.append(
                                f"{name}: {price:,.2f} ({change:+.2f}% today, {weekly:+.2f}% week)"
                            )
        
        if not document_parts:
            return
        
        document = '. '.join(document_parts)
        
        metadata = {
            'timestamp': timestamp,
            'date': date_int,  # ✅ Use integer
            'type': 'market'
        }
        
        self.market_collection.upsert(
            ids=[doc_id],
            documents=[document],
            metadatas=[metadata]
        )

    def store_analysis(self, analysis_type, content, timestamp=None):
        """Store AI analysis outputs (correlation, macro, micro)"""
        if not content:
            return
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        date_int = self._get_date_int(timestamp)
        date_str = timestamp[:10]
        doc_id = f"analysis_{analysis_type}_{date_str}"
        
        metadata = {
            'timestamp': timestamp,
            'date': date_int,  # ✅ Use integer
            'type': 'analysis',
            'analysis_type': analysis_type
        }
        
        self.analysis_collection.upsert(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata]
        )

    def store_backtest_results(self, backtest_stats, timestamp=None):
        """Store backtest accuracy results"""
        if not backtest_stats:
            return
        
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        date_int = self._get_date_int(timestamp)
        date_str = timestamp[:10]
        doc_id = f"backtest_{date_str}"
        
        accuracy = backtest_stats.get('accuracy_pct', 0)
        total = backtest_stats.get('total_evaluated', 0)
        wins = backtest_stats.get('total_wins', 0)
        
        document_parts = [f"Agent accuracy: {accuracy}% ({wins}/{total} predictions correct)"]
        
        recent = backtest_stats.get('recent_results', [])
        for r in recent:
            asset = r.get('asset', '')
            ai_label = r.get('ai_label', '')
            market_move = r.get('market_move', 0)
            correct = 'correct' if r.get('is_correct') else 'incorrect'
            document_parts.append(
                f"{asset}: AI predicted {ai_label}, market moved {market_move:+.2f}% ({correct})"
            )
        
        document = '. '.join(document_parts)
        
        metadata = {
            'timestamp': timestamp,
            'date': date_int,  # ✅ Use integer
            'type': 'backtest',
            'accuracy_pct': accuracy,
            'total_evaluated': total,
            'total_wins': wins
        }
        
        self.backtest_collection.upsert(
            ids=[doc_id],
            documents=[document],
            metadatas=[metadata]
        )

    # ==================== QUERY METHODS ====================

    def find_similar_news(self, query, limit=5, region=None, days_back=30):
        """Find news articles semantically similar to query"""
        if not query or self.news_collection.count() == 0:
            return []
        
        cutoff_date_int = int((datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d'))
        
        # Build where filter using $and for multiple conditions
        conditions = [{'type': 'news'}]
        if region:
            conditions.append({'region': region})
        conditions.append({'date': {'$gte': cutoff_date_int}})
        
        where_filter = {'$and': conditions} if len(conditions) > 1 else conditions[0]
        
        try:
            results = self.news_collection.query(
                query_texts=[query],
                n_results=min(limit, self.news_collection.count()),
                where=where_filter
            )
            
            similar_news = []
            if results and results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 0
                    similarity = max(0, 1 - (distance / 2))
                    
                    display_date = self._format_date_str(metadata.get('date', ''))
                    
                    similar_news.append({
                        'content': doc,
                        'metadata': {**metadata, 'date_str': display_date},
                        'similarity': round(similarity * 100, 1)
                    })
            
            return similar_news
        except Exception as e:
            print(f"    ⚠️  Similar news query failed: {e}")
            return []

    def get_sentiment_history(self, days_back=30):
        """Get sentiment snapshots over time"""
        if self.sentiment_collection.count() == 0:
            return []
        
        cutoff_date_int = int((datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d'))
        
        where_filter = {
            '$and': [
                {'type': 'sentiment'},
                {'date': {'$gte': cutoff_date_int}}
            ]
        }
        
        try:
            results = self.sentiment_collection.get(where=where_filter)
            
            history = []
            if results and results['documents']:
                for i, doc in enumerate(results['documents']):
                    metadata = results['metadatas'][i] if results['metadatas'] else {}
                    display_date = self._format_date_str(metadata.get('date', ''))
                    
                    history.append({
                        'content': doc,
                        'metadata': metadata,
                        'date': display_date,
                        'overall_score': metadata.get('overall_score', 0)
                    })
            
            history.sort(key=lambda x: x['date'])
            return history
        except Exception as e:
            print(f"    ⚠️  Sentiment history query failed: {e}")
            return []

    def find_similar_events(self, event_description, days_back=90, limit=5):
        """Find past events similar to current event"""
        return self.find_similar_news(event_description, limit=limit, days_back=days_back)

    def get_recent_analysis(self, analysis_type, days_back=7):
        """Get recent AI analysis of a specific type"""
        if self.analysis_collection.count() == 0:
            return []
        
        cutoff_date_int = int((datetime.now() - timedelta(days=days_back)).strftime('%Y%m%d'))
        
        where_filter = {
            '$and': [
                {'type': 'analysis'},
                {'analysis_type': analysis_type},
                {'date': {'$gte': cutoff_date_int}}
            ]
        }
        
        try:
            results = self.analysis_collection.get(where=where_filter)
            
            analyses = []
            if results and results['documents']:
                for i, doc in enumerate(results['documents']):
                    metadata = results['metadatas'][i] if results['metadatas'] else {}
                    display_date = self._format_date_str(metadata.get('date', ''))
                    
                    analyses.append({
                        'content': doc,
                        'metadata': metadata,
                        'date': display_date
                    })
            
            analyses.sort(key=lambda x: x['date'], reverse=True)
            return analyses
        except Exception as e:
            print(f"    ⚠️  Analysis query failed: {e}")
            return []

    def get_historical_context(self, current_news_summary, days_back=30):
        """
        Generate historical context string for AI prompts.
        Combines similar past events and sentiment trends.
        """
        context_parts = []
        
        similar = self.find_similar_news(current_news_summary, limit=3, days_back=days_back)
        if similar:
            context_parts.append("📚 SIMILAR PAST EVENTS:")
            for s in similar:
                date = s['metadata'].get('date_str', 'Unknown')
                region = s['metadata'].get('region_name', '')
                content = s['content'][:150] + '...' if len(s['content']) > 150 else s['content']
                similarity = s['similarity']
                context_parts.append(f"  • [{date}] {region}: {content} (similarity: {similarity}%)")
        
        sentiment_history = self.get_sentiment_history(days_back=14)
        if sentiment_history and len(sentiment_history) >= 3:
            recent_scores = [h['overall_score'] for h in sentiment_history[-7:]]
            avg_recent = sum(recent_scores) / len(recent_scores)
            trend = "improving" if recent_scores[-1] > recent_scores[0] + 10 else \
                    "deteriorating" if recent_scores[-1] < recent_scores[0] - 10 else "stable"
            
            context_parts.append(f"\n📈 14-DAY SENTIMENT TREND:")
            context_parts.append(f"  • Current: {recent_scores[-1]:+d}")
            context_parts.append(f"  • 7-day avg: {avg_recent:+.0f}")
            context_parts.append(f"  • Trend: {trend}")
        
        return '\n'.join(context_parts) if context_parts else ""

    def get_stats(self):
        """Get vector DB statistics"""
        return {
            'news_count': self.news_collection.count(),
            'sentiment_count': self.sentiment_collection.count(),
            'market_count': self.market_collection.count(),
            'analysis_count': self.analysis_collection.count(),
            'backtest_count': self.backtest_collection.count(),
            'persist_dir': self.persist_dir,
            'embedding_model': self.embedding_model
        }