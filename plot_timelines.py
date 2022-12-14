import os.path
import pathlib
import numpy as np
import pandas as pd
from matplotlib import dates as mdates, pyplot as plt, patches as mpatches, colors


def plot_pids_timeline_cpu_gpu(pid_names, title, start=None, end=None, xformat="%H:%M", margin=np.timedelta64(60, "s"), filename=None):
    pids = list(pid_names.keys())
    bar_height = 1
    ymins = [0, 1, 2]
    categories = ["BIO", "R/W", "OPEN"]
    colors_dict = dict(
        OPENAT="purple",
        READ="dodgerblue",
        WRITE="red",
        BIOR="blue",
        BIOW="red",
    )

    fig, axs = plt.subplots(
        nrows=len(pids) + 3,
        ncols=1,
        figsize=(30, len(pids) * 3),
        gridspec_kw={"height_ratios": [3] * (len(pids) + 2) + [1]},  # 1 for timeline
        sharex=True,
    )

    #
    # Plot CPU
    #
    df = pd.read_csv(
        os.path.join(DATA_DIR, "cpu_data/cpu_all.csv"),
        sep=",",
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if start is not None:
        df = df[df["timestamp"] > np.datetime64(start)]
    if end is not None:
        df = df[df["timestamp"] < np.datetime64(end)]

    ax = axs[0]
    ax.set_title("CPU Usage")
    ax.set_ylabel("percent utilisation(%)")

    # There are more fields available but weren't very interesting
    variables = [
        "%usr",
        "%sys",
        "%iowait",
        "%idle",
    ]

    n_features = len(variables)

    cm = plt.get_cmap("gist_rainbow")  # Colormap

    for i, var in enumerate(variables):
        line = ax.plot(df["timestamp"], df[var], label=var, linewidth=1)
        line[0].set_color(cm(1 * i / n_features))

    ax.grid(True, which="both", linestyle="--", color="grey", alpha=0.2)
    ax.tick_params(which="both", direction="in")

    ax.set_ylim(ymin=0)
    ax.legend(bbox_to_anchor=(1, 0.5), loc="center left")

    #
    # Plot GPU
    #
    df = pd.read_csv(os.path.join(DATA_DIR, "gpu_data/gpu_avg.csv"), sep=",")
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    if start is not None:
        df = df[df["timestamp"] > np.datetime64(start)]
    if end is not None:
        df = df[df["timestamp"] < np.datetime64(end)]

    ax1 = axs[1]
    ax1.set_title("GPU Usage")
    ax1.set_ylabel("percent utilisation(%)")

    ax1.plot(
        df["timestamp"],
        df["sm"],
        label="GPU MultiProcessor Use (%)",
        color="tab:red",
        linewidth=1,
        markersize=5,
    )
    ax1.plot(
        df["timestamp"],
        df["mem"],
        label="GPU Memory Use (%)",
        color="tab:orange",
        linewidth=1,
        markersize=5,
    )

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    ax2.set_ylabel("Size (MB)")
    ax2.plot(
        df["timestamp"],
        df["fb"],
        label="Framebuffer memory use (MB)",
        color="tab:blue",
        linewidth=1.5,
        markersize=5,
    )

    ax1.grid(True, which="both", linestyle="--")
    ax1.tick_params(which="both", direction="in", grid_color="grey", grid_alpha=0.2)

    ax1.set_ylim(ymin=0)
    ax2.set_ylim(ymin=0)

    ax1.legend(loc="center left")
    ax2.legend(loc="center right")


    #
    # Plot PIDs
    #
    for i, pid in enumerate(pids):
        print(f"Processing pid {pid}")

        df = pd.read_csv(
            os.path.join(DATA_DIR, f"st_end_data/st_end_data_{pid}"), names=["start_date", "end_date", "event"]
        )
        df = df[["start_date", "end_date", "event"]]
        df.start_date = pd.to_datetime(df.start_date).astype(np.datetime64)
        df.end_date = pd.to_datetime(df.end_date).astype(np.datetime64)

        if start is not None:
            df = df[df["start_date"] > np.datetime64(start)]
        if end is not None:
            df = df[df["end_date"] < np.datetime64(end)]

        # Can't define this earlier
        masks = {
            "BIO": (df["event"] == "BIOR") | (df["event"] == "BIOW"),
            "OPEN": (df["event"] == "OPENAT") ,
            "R/W": (df["event"] == "READ") | (df["event"] == "WRITE"),
        }

        ax = axs[i + 2]
        if pid in pid_names:
            ptitle = pid_names[pid] 
        else:
            ptitle = pid

        ax.set_title(f"{ptitle}")

        # Plot the events
        for j, category in enumerate(categories):
            mask = masks[category]
            start_dates = mdates.date2num(df.loc[mask].start_date)
            end_dates = mdates.date2num(df.loc[mask].end_date)
            durations = end_dates - start_dates
            xranges = list(zip(start_dates, durations))
            ymin = ymins[j] - 0.5
            yrange = (ymin, bar_height)
            colors = [colors_dict[event] for event in df.loc[mask].event]
            ax.broken_barh(xranges, yrange, facecolors=colors, alpha=1)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)

        ax.grid(True, axis="both", linestyle="--", linewidth=0.45, alpha=0.2, color="grey")
        ax.tick_params(which="both", direction="in")

        # Format the y-ticks
        ax.set_yticks(range(len(categories)))
        ax.set_yticklabels(categories)

        # Add the legend
        if i == 3:
            patches = [
                mpatches.Patch(color=color, label=key) for (key, color) in colors_dict.items()
            ]
            ax.legend(handles=patches, bbox_to_anchor=(1, 0.5), loc="center left")


    # Set the x axis limits
    # We do this here so that we create a margin around the trace data min/max vs. the timeline
    # data which we care less about. This makes the start/end setting work more as expected.
    if margin is None:
        margin = np.timedelta64(60, "s")

    ax.set_xlim(
        df.start_date.min() - margin,
        df.end_date.max() + margin,
    )


    #
    # Plot the timeline
    #
    print(f"Processing timeline")

    df = pd.read_csv(os.path.join(DATA_DIR, "mllog_data/timeline.csv"), names=["start_date", "end_date", "event"])

    df = df[["start_date", "end_date", "event"]]
    df.start_date = pd.to_datetime(df.start_date).astype(np.datetime64)
    df.end_date = pd.to_datetime(df.end_date).astype(np.datetime64)

    if start is not None:
        df = df[df["start_date"] > np.datetime64(start)]
    if end is not None:
        df = df[df["end_date"] < np.datetime64(end)]

    # Add synthetic data to show timeline info when no data point is included in the desired range
    # Uncomment/modify according to needs

    # if df.shape[0] == 0:
    #     print("empty will create default data")
    #     df.loc[-1] = [ np.datetime64(start),  np.datetime64(end), "EPOCH"]
    # # elif df.shape[0] == 1:

    # if title == "MLCommons Image Segmentation - 4 GPUs 1xRAM dataset - Naive Copy First 5 Min":
    #     init_period = df.iloc[0]
    #     print("pad end with epoch")
    #     df.loc[-1] = [ init_period["end_date"],  np.datetime64(end), "EPOCH"]
    #     print(df)
    #     print(df.shape)
    # elif title == "MLCommons Image Segmentation - 4 GPUs 1xRAM dataset - First Eval":
    #     print("Pad training with epochs")
    #     eval_period = df.iloc[0]
    #     eval_start = eval_period["start_date"] - np.timedelta64(1, "us")
    #     df.loc[-1] = [ np.datetime64(start),  eval_start, "EPOCH"]
    #     eval_stop = eval_period["end_date"] + np.timedelta64(1, "us")
    #     df.loc[-2] = [ eval_stop,  np.datetime64(end), "EPOCH"]
    #     print(df)
    #     print(df.shape)
    # else:
    if df.shape[0] == 0:
        print("Pad with epoch")
        df.loc[-1] = [ np.datetime64(start),  np.datetime64(end), "EPOCH"]

    categories = ["Timeline"]

    ymins = [0]
    colors_dict = dict(INIT="blue", FIRST_EPOCH="crimson", EPOCH="gold", EVAL="darkorchid")

    # Select the last axes
    ax = axs[-1]

    # Plot the events
    for i, _ in enumerate(categories):
        start_dates = mdates.date2num(df.start_date)
        end_dates = mdates.date2num(df.end_date)
        durations = end_dates - start_dates
        xranges = list(zip(start_dates, durations))
        ymin = ymins[i] - 0.5
        yrange = (ymin, bar_height)
        colors = [colors_dict[event] for event in df.event]
        # Plot vertical lines delimiting epoch starts
        ax.vlines(x=start_dates, ymin=ymin, ymax=0.5, color='k', linewidth=0.5)
        ax.broken_barh(xranges, yrange, facecolors=colors, alpha=0.8)
        # you can set alpha to 0.6 to check if there are some overlaps

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    # Add the legend
    patches = [mpatches.Patch(color=color, label=key) for (key, color) in colors_dict.items()]
    ax.legend(handles=patches, bbox_to_anchor=(1, 0.5), loc="center left")

    # TODO: Calculate the sort of timescale we're plotting and choose appropriate limits
    # Format the x-ticks
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=100))
    ax.xaxis.set_major_formatter(mdates.DateFormatter(
            xformat,
    ))

    # Format the y-ticks
    ax.set_yticks(range(len(categories)))
    ax.set_yticklabels(categories)

    ax.grid(True, axis="x", linestyle="--", linewidth=0.45, alpha=0.2, color="grey")
    ax.tick_params(axis="x", which="both", direction="out", rotation=30)

    print("Saving figure")

    fig.suptitle(title)

    if filename is not None:
        filename = filename
    else:
        filename = "timelines/cpu_gpu_timeline"
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(filename)
    pathlib.Path(os.path.join("./plots/", output_dir)).mkdir(parents=True, exist_ok=True)

    plt.savefig(f"./plots/{filename}.png", format="png", dpi=500)


if __name__ == "__main__":

    print("This is the old version of the timeline plotting script. Please use timeline.py instead.\n")
    exit(0)

    DATA_DIR = "data/ta_4gpu_1xRAM_ref"

    # TODO: Automate this process. Would need to extract relevant PIDs from the many that show up
    # and find a way to ID which is which. Else this will remain manual.
    # Even better: use the output of ps aux to ID which is the master and which are the 

    pid_names = {
        "65757": "main process",
        "65758": "worker 1",        
        "65759": "worker 2",
        "65760": "worker 3",
        "65761": "worker 4",
    }

    plot_pids_timeline_cpu_gpu(
        pid_names,
        title="Image Segmentation - 4 GPUs 1xRAM dataset - run w DDP launch.py",
        filename="timelines/1xRAM_ref/4gpus_1xRAM_ref",
    )

    exit(0)


    DATA_DIR = "data/ta_4gpu_1xRAM"

    pids = [
        "33677",    #master
        "33710",    # RT
        "33711",
        "33712",
        "33713",
        "33714",
    ]

    pid_names = {
        "33677": "master process",
        "33710": "resource tracker", 
        "33711": "worker 1",        
        "33712": "worker 2",
        "33713": "worker 3",
        "33714": "worker 4",
    }

    plot_pids_timeline_cpu_gpu(
        pid_names,
        title="Image Segmentation - 4 GPUs 1xRAM dataset",
        filename="timelines/1xRAM/4gpus_1xRAM",
    )

    plot_pids_timeline_cpu_gpu(
        pid_names,
        title="Image Segmentation - 4 GPUs 1xRAM dataset - First 5 Minutes",
        start="2022-04-29T19:29:25",
        end="2022-04-29T19:34:25",
        xformat="%H:%M:%S",
        margin=np.timedelta64(1, "s"),
        filename="timelines/1xRAM/4gpus_1xRAM_first5min",
    )

    plot_pids_timeline_cpu_gpu(
        pid_names,
        title="Image Segmentation - 4 GPUs 1xRAM dataset - Last Moments",
        start="2022-04-30T02:03:45",
        end="2022-04-30T02:04:05",
        xformat="%H:%M:%S",
        margin=np.timedelta64(500, "ms"),
        filename="timelines/1xRAM/4gpus_1xRAM_last_moments",
    )

    plot_pids_timeline_cpu_gpu(
        pid_names,
        title="Image Segmentation - 4 GPUs 1xRAM dataset - First Eval",
        start="2022-04-29T22:28:40",
        end="2022-04-29T22:31:00",
        xformat="%H:%M:%S",
        margin=np.timedelta64(5, "s"),
        filename="timelines/1xRAM/4gpus_1xRAM_first_eval",
    )




    # DATA_DIR = "data/ta_4gpus_100gb"

    # pids = [
    #     "16910",    #master
    #     "16943",    # RT
    #     "16944",
    #     "16945",
    #     "16946",
    #     "16947",
    # ]

    # pid_names = {
    #     "16910": "master process",
    #     "16943": "resource tracker", 
    #     "16944": "worker 1",        
    #     "16945": "worker 2",
    #     "16946": "worker 3",
    #     "16947": "worker 4",
    # }

    # plot_pids_timeline_cpu_gpu(
    #     pid_names,
    #     title="Image Segmentation - 4 GPUs, 100GB dataset",
    #     filename="timelines/100gb/4gpus_100gb",
    # )

    # plot_pids_timeline_cpu_gpu(
    #     pid_names,
    #     title="Image Segmentation - 4 GPUs, 100GB dataset - First 5 Minutes",
    #     start="2022-05-11T22:49:07",
    #     end="2022-05-11T22:54:07",
    #     xformat="%H:%M:%S",
    #     margin=np.timedelta64(10, "s"),
    #     filename="timelines/100gb/4gpus_100gb_first5min",
    # )

    # plot_pids_timeline_cpu_gpu(
    #     pid_names,
    #     title="Image Segmentation - 4 GPUs, 100GB dataset - Last Moments",
    #     start="2022-05-12T01:15:30",
    #     end="2022-05-12T01:15:40",
    #     xformat="%H:%M:%S",
    #     margin=np.timedelta64(500, "ms"),
    #     filename="timelines/100gb/4gpus_100gb_last_moments",
    # )

    # plot_pids_timeline_cpu_gpu(
    #     pid_names,
    #     title="Image Segmentation - 4 GPUs, 100GB dataset - First Eval",
    #     start="2022-05-11T23:50:47",
    #     end="2022-05-11T23:52:58",
    #     xformat="%H:%M:%S",
    #     margin=np.timedelta64(5, "s"),
    #     filename="timelines/100gb/4gpus_100gb_first_eval",
    # )


    # plot_pids_timeline_cpu_gpu(
    #     pid_names,
    #     title="MLCommons Image Segmentation - 4 GPUs Baseline - First Eval Period",
    #     start="2022-04-29T18:30:30",
    #     end="2022-04-29T18:33:30",
    #     xformat="%H:%M:%S",
    #     margin=np.timedelta64(5, "s"),
    #     filename="timelines/4gpu_baseline_firsteval",
    # )
