import { createBrowserRouter } from 'react-router-dom'
import { App } from './App'
import { AboutPage } from '../pages/AboutPage'
import { DatabasePage } from '../pages/DatabasePage'
import { ServicePage } from '../pages/ServicePage'
import { SimulationPage } from '../pages/SimulationPage'
import { TeamPage } from '../pages/TeamPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <ServicePage /> },
      { path: 'about', element: <AboutPage /> },
      { path: 'database', element: <DatabasePage /> },
      { path: 'db', element: <DatabasePage /> },
      { path: 'simulation', element: <SimulationPage /> },
      { path: 'sim', element: <SimulationPage /> },
      { path: 'team', element: <TeamPage /> },
    ],
  },
])
