import "./styles.css";
import { createAccountApp } from "./accountApp.js";

const app = createAccountApp();
app.start();
if (import.meta.hot) import.meta.hot.dispose(() => app.stop());
