// Shows the prompt Grok returned inside the node after each run.
import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "GrokPromptMaker.ShowPrompt",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "GrokPromptMaker") return;
        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            onExecuted?.apply(this, arguments);
            const text = (message?.text || []).join("\n");
            let w = this.widgets?.find((x) => x.name === "result");
            if (!w) {
                w = ComfyWidgets["STRING"](this, "result", ["STRING", { multiline: true }], app).widget;
                w.inputEl.readOnly = true;
                w.inputEl.style.opacity = 0.75;
                w.serialize = false; // display only: not saved with the workflow
                const size = this.computeSize();
                this.setSize([Math.max(this.size[0], size[0]), Math.max(this.size[1], size[1] + 120)]);
            }
            w.value = text;
            this.setDirtyCanvas(true, true);
        };
    },
});
