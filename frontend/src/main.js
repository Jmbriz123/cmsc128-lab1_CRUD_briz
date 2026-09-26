import "./styles.css";

import { mountApp } from "./components/appShell.js";
import { bindTaskHandlers } from "./handlers/taskHandlers.js";

const elements = mountApp();
bindTaskHandlers(elements);
