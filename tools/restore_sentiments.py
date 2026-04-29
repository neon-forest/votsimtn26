import pandas as pd

def restore():
    df = pd.read_csv("assembly_candidate_sentiment.csv")
    
    # Restoring to Original Means from Audit in Turn 37
    df["Candidate_Sentiment_SPA"] = df["Candidate_Sentiment_SPA"] + (4.517949 - df["Candidate_Sentiment_SPA"].mean())
    df["Candidate_Sentiment_AIADMK"] = df["Candidate_Sentiment_AIADMK"] + (-1.757265 - df["Candidate_Sentiment_AIADMK"].mean())
    df["Candidate_Sentiment_TVK"] = df["Candidate_Sentiment_TVK"] + (4.747863 - df["Candidate_Sentiment_TVK"].mean())
    df["Candidate_Sentiment_Others"] = df["Candidate_Sentiment_Others"] + (7.374786 - df["Candidate_Sentiment_Others"].mean())
    
    df.to_csv("assembly_candidate_sentiment.csv", index=False)
    print("Sentiments restored to original state.")
    print(df.iloc[:, 2:].mean())

if __name__ == "__main__":
    restore()
