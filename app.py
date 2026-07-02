import gradio as gr
import subprocess, pandas as pd

def run_ranker(n_samples):
    subprocess.run(["python", "pipeline/rank.py", "--limit", str(n_samples), "--output", "out.csv"])
    return pd.read_csv("out.csv")

demo = gr.Interface(
    fn=run_ranker,
    inputs=gr.Slider(10, 200, value=50, label="Number of sample candidates"),
    outputs=gr.Dataframe(),
    title="Redrob Ranker Sandbox"
)
demo.launch()