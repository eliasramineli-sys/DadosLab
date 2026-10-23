import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

BG = "#111e32"
TEXT = "#b2c3dc"
ACCENT = "#64dcc7"


class Charts(FigureCanvasQTAgg):
    def __init__(self):
        self.figure = Figure(figsize=(8,5.6), facecolor=BG, layout="constrained")
        super().__init__(self.figure)
        self.setMinimumSize(400,400)
        self.axes = self.figure.subplots(2,1)

    def refresh(self, values, result):
        for ax in self.axes:
            ax.clear()
            ax.set_facecolor(BG)
            ax.tick_params(colors=TEXT,labelsize=9)
            ax.spines[["top","right"]].set_visible(False)
            for spine in ax.spines.values(): spine.set_color("#34455f")
            ax.grid(axis="y",color="#263951",alpha=.6,linewidth=.6)
            ax.set_axisbelow(True)
        top,bottom=self.axes
        top.set_title("Distribuição das faces",color="white",loc="left",fontsize=12,pad=14)
        selected=result["selected"]
        rows=result["table"]
        heights=np.array([r["frequencia"] for r in rows])*100
        top.bar(range(1,7),heights,color=[ACCENT if i==selected else "#5082cf" for i in range(1,7)],width=.58,zorder=3)
        if values:
            errors=np.array([[max(0,(r['frequencia']-r['ic95_inferior'])*100) for r in rows],
                [max(0,(r['ic95_superior']-r['frequencia'])*100) for r in rows]])
            top.errorbar(range(1,7),heights,yerr=errors,fmt="none",ecolor="#d0ddf0",capsize=4,zorder=4)
        top.axhline(100/6,color="#ffce85",linestyle="--",linewidth=1.2,label="Teórica: 16,67%")
        top.set_xticks(range(1,7),[f"Face {i}" for i in range(1,7)])
        top.set_ylabel("Frequência (%)",color=TEXT,fontsize=9)
        top.set_ylim(0,max(35,max([r['ic95_superior']*100 for r in rows]) + 5) if values else 40)
        legend=top.legend(loc="upper right",facecolor=BG,edgecolor="none",fontsize=8)
        for text in legend.get_texts(): text.set_color(TEXT)
        bottom.set_title(f"Convergência da face {selected}",color="white",loc="left",fontsize=12,pad=14)
        if values:
            count=np.cumsum(np.array(values)==selected)
            steps=np.arange(1,len(values)+1)
            indices=np.unique(np.linspace(0,len(values)-1,min(1500,len(values)),dtype=int))
            bottom.plot(steps[indices],100*count[indices]/steps[indices],color=ACCENT,linewidth=1.6)
        else:
            bottom.text(.5,.5,"Os gráficos começam no primeiro lançamento",ha="center",va="center",transform=bottom.transAxes,color=TEXT,fontsize=10)
        bottom.axhline(100/6,color="#ffce85",linestyle="--",linewidth=1)
        bottom.set_xlabel("Número de lançamentos",color=TEXT,fontsize=9)
        bottom.set_ylabel("Frequência acumulada (%)",color=TEXT,fontsize=9)
        bottom.set_ylim(0,100)
        self.draw_idle()
