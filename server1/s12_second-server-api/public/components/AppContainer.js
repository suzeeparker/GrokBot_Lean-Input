// import { Panel } from './Panel.js';
// import { LogViewer } from './LogViewer.js';

export class AppContainer {

  constructor(mountPoint) {
    this.mountPoint = mountPoint;
    this.render();
    this.initElements();
  }

  render() {
    this.mountPoint.innerHTML = `
      <header>
        <h1>App C21</h1>
      </header>
      <main class="card">
        <div id="card1"></div>
      </main>
    `;
  }

  initElements() { }
}

// Instantiate App entry on DOM completion
window.addEventListener('DOMContentLoaded', () => {
  new AppContainer(document.getElementById('app-root'));
});
