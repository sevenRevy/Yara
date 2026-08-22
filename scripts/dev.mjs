import { spawn } from "node:child_process";

const children = new Set();
let shuttingDown = false;
const frontendCommand = "npm run dev";
const streamlitCommand =
  process.platform === "win32"
    ? "py -3 -m streamlit run backend/api/app.py"
    : "python3 -m streamlit run backend/api/app.py";

function start(label, commandLine) {
  const child = spawn(commandLine, {
    stdio: "inherit",
    shell: true,
  });

  children.add(child);
  child.on("error", (error) => {
    if (shuttingDown) {
      return;
    }

    console.error(`[${label}] failed to start.`);
    console.error(error);
    shutdown(1);
  });

  return child;
}

function shutdown(code) {
  if (shuttingDown) {
    return;
  }

  shuttingDown = true;
  for (const child of children) {
    child.kill();
  }

  process.exit(code);
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

console.log("Starting frontend and Streamlit...");
start("frontend", frontendCommand);
start("streamlit", streamlitCommand);
