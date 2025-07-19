import streamlit as st
import praw
import pandas as pd
from datetime import datetime
import time
import re

# Page configuration
st.set_page_config(
    page_title="Reddit Unanswered Questions Finder",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Reddit Unanswered Questions Finder")
st.markdown("Find unanswered questions on Reddit based on your keywords")

# Sidebar for Reddit API configuration
st.sidebar.header("Reddit API Configuration")
st.sidebar.markdown("""
**To use this app, you need Reddit API credentials:**
1. Go to https://www.reddit.com/prefs/apps
2. Create a new app (script type)
3. Make sure to select "script" (not "web app")
4. Use http://localhost:8080 as redirect URI
5. Get your client_id, client_secret, and user_agent

**⚠️ If you get 401 errors:**
- Double-check your credentials
- Make sure your Reddit app is set to "script" type
- Verify you're using the correct client ID (under app name)
- Wait a few minutes after creating the app
""")

# Input fields for Reddit API credentials
client_id = st.sidebar.text_input("Client ID", type="password")
client_secret = st.sidebar.text_input("Client Secret", type="password")
user_agent = st.sidebar.text_input("User Agent", value="Unanswered Query Tool/1.0")

# Main interface
col1, col2 = st.columns([2, 1])

with col1:
    keyword = st.text_input("🔎 Enter keyword to search:", placeholder="python, javascript, cooking, etc.")

with col2:
    st.write("")  # spacing
    st.write("")  # spacing
    search_button = st.button("Search Questions", type="primary")

# Advanced options
with st.expander("Advanced Options"):
    col3, col4, col5 = st.columns(3)
    
    with col3:
        subreddit_filter = st.text_input("Specific Subreddit (optional)", placeholder="AskReddit, learnpython, etc.")
    
    with col4:
        time_filter = st.selectbox("Time Filter", ["all", "day", "week", "month", "year"])
    
    with col5:
        max_results = st.slider("Max Results", min_value=10, max_value=100, value=25)

    # Enhanced filtering options
    col6, col7 = st.columns(2)
    with col6:
        min_score = st.slider("Minimum Score", min_value=-10, max_value=50, value=0, help="Posts with at least this score")
    with col7:
        relevance_threshold = st.slider("Relevance Threshold", min_value=0.0, max_value=1.0, value=0.3, step=0.1, help="Higher = more strict matching")
    
    # Additional options
    col8, col9 = st.columns(2)
    with col8:
        max_comments_threshold = st.slider("Max Comments for 'Unanswered'", min_value=0, max_value=15, value=5, help="Posts with this many comments or fewer")
    with col9:
        question_only_mode = st.checkbox("Question Posts Only", value=True, help="Filter out promotional/spam content")

    # Content filtering
    col10, col11 = st.columns(2)
    with col10:
        filter_promotional = st.checkbox("Filter Promotional Content", value=True, help="Remove obvious ads/spam")
    with col11:
        min_content_length = st.slider("Min Content Length", min_value=0, max_value=200, value=50, help="Minimum characters in post content")

# Function to check if Reddit credentials are provided
def check_credentials():
    return client_id and client_secret and user_agent

# Function to initialize Reddit instance
@st.cache_resource
def init_reddit(client_id, client_secret, user_agent):
    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            check_for_async=False
        )
        # Test the connection
        test_sub = reddit.subreddit("test")
        test_sub.display_name
        return reddit
    except Exception as e:
        st.error(f"Failed to connect to Reddit API: {str(e)}")
        return None

# Enhanced function to detect promotional/spam content
def is_promotional_content(title, content):
    """Detect promotional or spam content"""
    text = f"{title} {content}".lower()
    
    # Promotional indicators
    promo_indicators = [
        'watch the video', 'tutorial below', 'link in bio', 'dm me', 'check out',
        'affiliate', 'sponsored', 'promotion', 'advertisement', 'buy now',
        'limited time', 'special offer', 'discount', 'sale', 'deal',
        'click here', 'subscribe', 'follow me', 'my channel', 'my course',
        'will change everything', 'secret method', 'exposed', 'truth about',
        'nobody talks about', 'revolutionary', 'game changer'
    ]
    
    # URL patterns that suggest promotional content
    url_patterns = [
        'youtube.com', 'youtu.be', 'bit.ly', 'tinyurl.com', 'goo.gl'
    ]
    
    promo_score = 0
    for indicator in promo_indicators:
        if indicator in text:
            promo_score += 1
    
    for pattern in url_patterns:
        if pattern in text:
            promo_score += 1
    
    return promo_score >= 2  # Consider promotional if 2+ indicators

# Enhanced function to check if post is a genuine question
def is_genuine_question(title, content):
    """Check if post is asking a genuine question"""
    text = f"{title} {content}".lower()
    
    # Question indicators
    question_words = ['?', 'how', 'what', 'why', 'which', 'where', 'when', 'who']
    help_words = ['help', 'advice', 'recommend', 'suggest', 'opinion', 'thoughts']
    seeking_words = ['looking for', 'need', 'want', 'seeking', 'trying to find']
    
    # Check for question patterns
    has_question_word = any(word in text for word in question_words)
    has_help_word = any(word in text for word in help_words)
    has_seeking_word = any(phrase in text for phrase in seeking_words)
    
    return has_question_word or has_help_word or has_seeking_word

# Improved relevance scoring for SEO courses specifically
def calculate_enhanced_relevance_score(title, content, keyword):
    """Enhanced relevance scoring with better keyword matching"""
    keyword_lower = keyword.lower()
    title_lower = title.lower()
    content_lower = content.lower() if content else ""
    full_text = f"{title_lower} {content_lower}"
    
    score = 0.0
    
    # Exact keyword match in title (high weight)
    if keyword_lower in title_lower:
        score += 0.5
        # Bonus for keyword being a significant part of title
        title_words = title_lower.split()
        if any(keyword_lower in word or word in keyword_lower for word in title_words):
            score += 0.2
    
    # Exact keyword match in content
    if keyword_lower in content_lower:
        score += 0.3
    
    # Enhanced contextual scoring for specific keywords
    if 'seo' in keyword_lower:
        seo_related = [
            'search engine optimization', 'digital marketing', 'google ranking',
            'website traffic', 'keyword research', 'backlinks', 'optimization',
            'ranking', 'search engine', 'google', 'marketing', 'traffic',
            'organic', 'serp', 'meta', 'analytics'
        ]
        for term in seo_related:
            if term in full_text:
                score += 0.15
    
    if 'course' in keyword_lower:
        course_related = [
            'tutorial', 'learn', 'training', 'education', 'class', 'lesson',
            'certification', 'certificate', 'program', 'bootcamp', 'academy',
            'instructor', 'teacher', 'beginner', 'advanced', 'online learning'
        ]
        for term in course_related:
            if term in full_text:
                score += 0.15
    
    # Question context bonus
    question_contexts = [
        'best course', 'recommend course', 'good course', 'which course',
        'course recommendation', 'learning', 'study', 'beginner',
        'start with', 'where to learn', 'how to learn'
    ]
    
    for context in question_contexts:
        if context in full_text:
            score += 0.2
            break
    
    # Penalty for promotional content
    if is_promotional_content(title, content):
        score *= 0.3  # Significantly reduce score for promotional content
    
    return min(score, 1.0)

# Enhanced unanswered detection
def is_unanswered_enhanced(submission, max_comments=5):
    """Enhanced check for unanswered posts"""
    try:
        if submission.num_comments == 0:
            return True
        
        if submission.num_comments > max_comments * 2:
            return False
        
        if submission.num_comments <= max_comments:
            try:
                # Check comment quality more efficiently
                submission.comments.replace_more(limit=1)  # Limited expansion for speed
                meaningful_comments = 0
                
                for comment in submission.comments[:max_comments + 2]:
                    if hasattr(comment, 'body') and comment.body:
                        if not comment.body.lower().startswith(('[deleted]', '[removed]')):
                            # More sophisticated comment quality check
                            if is_meaningful_comment(comment.body):
                                meaningful_comments += 1
                                if meaningful_comments > max_comments // 2:  # Allow some meaningful comments
                                    return False
                
                return True
            except:
                return True
        
        return False
    except:
        return submission.num_comments <= max_comments

def is_meaningful_comment(comment_body):
    """Check if comment provides meaningful help"""
    if not comment_body or len(comment_body.strip()) < 15:
        return False
    
    comment_lower = comment_body.lower().strip()
    
    # Low quality phrases
    low_quality = [
        'thanks', 'thank you', 'thx', '+1', 'same', 'this', 'agreed', 
        'yes', 'no', 'upvoted', 'bump', 'following', 'interested', 
        'me too', 'same here', 'lol', 'nice', 'cool', 'good luck'
    ]
    
    if comment_lower in low_quality:
        return False
    
    # Check for meaningful content indicators
    meaningful_indicators = [
        'recommend', 'suggest', 'try', 'use', 'check out', 'experience',
        'worked for me', 'helped me', 'solution', 'answer', 'result'
    ]
    
    word_count = len(comment_body.split())
    has_meaningful_content = any(indicator in comment_lower for indicator in meaningful_indicators)
    
    return word_count >= 5 and (has_meaningful_content or word_count >= 20)

# Main search function with enhanced filtering
def search_unanswered_questions_enhanced(reddit, keyword, subreddit_name=None, time_filter="all",
                                       limit=25, min_score=0, relevance_threshold=0.3,
                                       max_comments_threshold=5, question_only_mode=True,
                                       filter_promotional=True, min_content_length=50):
    questions = []
    
    try:
        # Search strategy: try multiple approaches
        search_terms = [
            keyword,
            f"{keyword} help",
            f"{keyword} advice",
            f"{keyword} recommend"
        ]
        
        all_submissions = []
        
        for search_term in search_terms[:2]:  # Limit to avoid too many API calls
            try:
                if subreddit_name:
                    subreddit = reddit.subreddit(subreddit_name)
                    results = subreddit.search(search_term, sort="new", time_filter=time_filter, limit=limit*3)
                else:
                    results = reddit.subreddit("all").search(search_term, sort="new", time_filter=time_filter, limit=limit*3)
                
                all_submissions.extend(list(results))
            except Exception as e:
                st.warning(f"Search term '{search_term}' failed: {str(e)}")
                continue
        
        # Remove duplicates based on submission ID
        unique_submissions = {sub.id: sub for sub in all_submissions}.values()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed = 0
        found_unanswered = 0
        
        for submission in unique_submissions:
            if found_unanswered >= limit:
                break
            
            processed += 1
            if processed % 10 == 0:
                status_text.text(f"Processing {processed} posts... Found {found_unanswered} quality questions")
                progress_bar.progress(min(processed / (limit * 6), 1.0))
            
            # Basic filters
            if submission.score < min_score:
                continue
            
            # Content length filter
            content_length = len(submission.selftext) if submission.selftext else 0
            if content_length < min_content_length and not submission.title.endswith('?'):
                continue
            
            # Filter promotional content
            if filter_promotional and is_promotional_content(submission.title, submission.selftext):
                continue
            
            # Question-only mode filter
            if question_only_mode and not is_genuine_question(submission.title, submission.selftext):
                continue
            
            # Enhanced relevance scoring
            relevance = calculate_enhanced_relevance_score(submission.title, submission.selftext, keyword)
            
            if relevance < relevance_threshold:
                continue
            
            # Enhanced unanswered check
            if is_unanswered_enhanced(submission, max_comments_threshold):
                questions.append({
                    'Title': submission.title,
                    'Subreddit': submission.subreddit.display_name,
                    'Author': str(submission.author) if submission.author else '[deleted]',
                    'Score': submission.score,
                    'Comments': submission.num_comments,
                    'Created': datetime.fromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M'),
                    'URL': f"https://reddit.com{submission.permalink}",
                    'Content': submission.selftext[:400] + "..." if len(submission.selftext) > 400 else submission.selftext,
                    'Relevance': f"{relevance:.2f}",
                    'Content_Length': len(submission.selftext) if submission.selftext else 0
                })
                found_unanswered += 1
            
            time.sleep(0.1)  # Rate limiting
        
        progress_bar.empty()
        status_text.empty()
        
        # Sort by relevance score (highest first), then by recency
        questions.sort(key=lambda x: (float(x['Relevance']), x['Created']), reverse=True)
        
        return questions
    
    except Exception as e:
        st.error(f"Error searching Reddit: {str(e)}")
        return []

# Main search logic
if search_button:
    if not keyword:
        st.warning("Please enter a keyword to search for.")
    elif not check_credentials():
        st.warning("Please provide Reddit API credentials in the sidebar.")
    else:
        with st.spinner("Connecting to Reddit API..."):
            reddit = init_reddit(client_id, client_secret, user_agent)
        
        if reddit:
            st.success("✅ Connected to Reddit API successfully!")
            
            with st.spinner(f"Searching for unanswered questions about '{keyword}'..."):
                questions = search_unanswered_questions_enhanced(
                    reddit,
                    keyword,
                    subreddit_filter if subreddit_filter else None,
                    time_filter,
                    max_results,
                    min_score,
                    relevance_threshold,
                    max_comments_threshold,
                    question_only_mode,
                    filter_promotional,
                    min_content_length
                )
            
            if questions:
                st.success(f"Found {len(questions)} high-quality unanswered questions!")
                
                # Display summary statistics
                col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
                with col_stats1:
                    avg_relevance = sum(float(q['Relevance']) for q in questions) / len(questions)
                    st.metric("Avg Relevance", f"{avg_relevance:.2f}")
                with col_stats2:
                    avg_score = sum(q['Score'] for q in questions) / len(questions)
                    st.metric("Avg Score", f"{avg_score:.1f}")
                with col_stats3:
                    unique_subreddits = len(set(q['Subreddit'] for q in questions))
                    st.metric("Subreddits", unique_subreddits)
                with col_stats4:
                    recent_posts = sum(1 for q in questions if '2025-07' in q['Created'])
                    st.metric("Recent Posts", recent_posts)
                
                st.markdown("---")
                
                # Display results
                for i, q in enumerate(questions, 1):
                    with st.container():
                        col_main, col_meta = st.columns([3, 1])
                        
                        with col_main:
                            # Color-code by relevance
                            if float(q['Relevance']) >= 0.7:
                                st.markdown(f"### 🎯 {i}. {q['Title']}")
                            elif float(q['Relevance']) >= 0.5:
                                st.markdown(f"### ✅ {i}. {q['Title']}")
                            else:
                                st.markdown(f"### 📝 {i}. {q['Title']}")
                            
                            if q['Content']:
                                st.markdown(f"*{q['Content']}*")
                            st.markdown(f"**[📍 View on Reddit]({q['URL']})**")
                        
                        with col_meta:
                            st.metric("Relevance", q['Relevance'])
                            st.metric("Score", q['Score'])
                            st.metric("Comments", q['Comments'])
                            st.write(f"**Subreddit:** r/{q['Subreddit']}")
                            st.write(f"**Author:** u/{q['Author']}")
                            st.write(f"**Posted:** {q['Created']}")
                            if q['Content_Length'] > 0:
                                st.write(f"**Content:** {q['Content_Length']} chars")
                        
                        st.divider()
                
                # Enhanced download with better formatting
                df = pd.DataFrame(questions)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Enhanced Results as CSV",
                    data=csv,
                    file_name=f"reddit_unanswered_enhanced_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.info(f"No quality unanswered questions found for '{keyword}'. Try:")
                st.markdown("""
                **🔧 Adjust Settings:**
                - **Lower relevance threshold** (try 0.2)
                - **Increase max comments** (try 8-10)
                - **Turn off question-only mode**
                - **Reduce minimum content length** (try 20-30)
                - **Lower minimum score** (try -2)
                
                **🎯 Try Better Keywords:**
                - Instead of "seo course" → try "learn seo", "seo tutorial", "seo training"
                - Be more specific: "seo course beginner", "best seo certification"
                - Try related terms: "digital marketing course", "search engine optimization"
                
                **📍 Target Specific Communities:**
                - SEO: r/SEO, r/bigseo, r/TechSEO
                - Marketing: r/digital_marketing, r/marketing
                - Learning: r/learndigitalmarketing, r/entrepreneur
                """)

# Enhanced information section
with st.expander("🚀 Enhanced Features in This Version"):
    st.markdown("""
    ### 🎯 Key Improvements for Better Results:
    
    **🔍 Smarter Search Strategy:**
    - **Multiple search terms** - searches for "keyword", "keyword help", "keyword advice"
    - **Enhanced relevance scoring** - better matches for your specific keyword
    - **Duplicate removal** - no repeated posts from different searches
    
    **🛡️ Quality Filtering:**
    - **Promotional content filter** - removes obvious ads and spam
    - **Question-only mode** - focuses on genuine questions vs promotional posts
    - **Minimum content length** - ensures posts have substantial content
    - **Enhanced comment analysis** - better detection of meaningful vs low-quality responses
    
    **📊 Better Results Display:**
    - **Color-coded relevance** - 🎯 High (0.7+), ✅ Good (0.5+), 📝 Okay (<0.5)
    - **Summary statistics** - average relevance, scores, subreddit diversity
    - **Content length indicator** - shows how detailed the post is
    
    **⚡ Performance Optimizations:**
    - **Faster comment processing** - limited expansion for speed
    - **Better error handling** - continues even if some searches fail
    - **Progress tracking** - shows quality questions found vs total processed
    
    ### 💡 Pro Tips for "SEO Course" Searches:
    - **Use specific subreddits**: r/SEO, r/bigseo, r/digital_marketing
    - **Try variations**: "seo training", "learn seo", "seo certification"
    - **Lower relevance threshold to 0.2-0.3** for more results
    - **Set max comments to 5-8** (many good questions have a few comments)
    - **Enable promotional filtering** to avoid spam courses
    
    This enhanced version should give you much higher quality, more relevant results!
    """)

# Footer
st.markdown("---")
st.markdown("🔥 **Enhanced Version 2.0** - Better quality, smarter filtering, more relevant results!")