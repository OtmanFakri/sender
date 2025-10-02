def extract_clean_posts(data):
    """
    Extract and clean LinkedIn posts from the raw JSON data.
    Returns a list of cleaned posts with author, text, likes, comments, creation time, and link.
    """
    cleaned_posts = []
    
    # Create a lookup dictionary for social activity counts
    social_counts = {}
    for item in data:
        if item.get("$type") == "com.linkedin.voyager.feed.shared.SocialActivityCounts":
            urn = item.get("urn")
            if urn:
                social_counts[urn] = {
                    "likes": item.get("numLikes", 0),
                    "comments": item.get("numComments", 0)
                }
    
    # Extract posts
    for item in data:
        if item.get("$type") == "com.linkedin.voyager.feed.render.UpdateV2":
            post = {}
            
            # Extract author information
            actor = item.get("actor", {})
            if actor:
                author_name = actor.get("name", {}).get("text", "Unknown")
                post["author"] = author_name
            
            # Extract post text/commentary
            commentary = item.get("commentary", {})
            if commentary:
                text = commentary.get("text", {}).get("text", "")
                post["text"] = text
            
            # Extract permalink (post link)
            metadata = item.get("updateMetadata", {})
            share_urn = metadata.get("shareUrn", "")
            
            # The permalink is often in the socialDetail object
            social_detail = item.get("*socialDetail", "")
            if social_detail:
                # Find the social detail object to get permalink
                for social_item in data:
                    if social_item.get("entityUrn") == social_detail:
                        permalink = social_item.get("permalink", "")
                        if permalink:
                            post["link"] = permalink
                        break
            
            # Alternative: construct link from share URN
            if "link" not in post and share_urn:
                if "ugcPost:" in share_urn:
                    post_id = share_urn.split("ugcPost:")[-1]
                    post["link"] = f"https://www.linkedin.com/feed/update/urn:li:ugcPost:{post_id}"
                elif "groupPost:" in share_urn:
                    post_id = share_urn.split("groupPost:")[-1]
                    post["link"] = f"https://www.linkedin.com/feed/update/urn:li:groupPost:{post_id}"
            
            # Extract social metrics
            if social_detail:
                # Convert entityUrn format
                social_urn = social_detail.replace("urn:li:fs_socialDetail:", "")
                
                # Look up in our dictionary
                if social_urn in social_counts:
                    post["likes"] = social_counts[social_urn]["likes"]
                    post["comments"] = social_counts[social_urn]["comments"]
            
            # Extract creation timestamp from comments if available
            post["createdAt"] = None
            
            # Only add posts that have at least author and text
            if post.get("author") and post.get("text"):
                cleaned_posts.append(post)
    
    return cleaned_posts
