"""An offshore wind farm model

@moduleauthor:: Juan P. Murcia <jumu@dtu.dk>

"""
import numpy as np
MATPLOTLIB = True
try:
    import matplotlib.pyplot as plt
except Exception as e:
    MATPLOTLIB = False
    print("WARNING: Matplotlib isn't installed correctly:", e)

from .WindTurbine import WindTurbineDICT
from windIO.Plant import WTLayout

class WindTurbineList(list):
    """A simple list class that can also act as a single element when needed.
    Accessing one of the attribute of this list will get the first element of the
    list attributes.

    Note
    ----
    We assume here that if a model call this intense as if it's one wind
    turbine, the user has been clever enough to pass as input a wind farm with
    identical turbines.
    """
    def __getattr__(self, key):
        #TODO: make some checks to catch possible bugs when the turbines are not similar.
        return getattr(self.__getitem__(0), key)

    def names(self):
        return [getattr(w, 'name') for w in self]


class WindFarm(object):
    def __init__(self, name=None, yml=None, coordFile=None, array=None, WT=None):
    #def __init__(self, name, yml=None, coordFile, WT):
        """Initializes a WindFarm object.
        The initialization can be done using a `windIO` yml file or using a
        coodFile + WindTurbine instance.

        Parameters
        ----------
        name: str, optional
            WindFarm name
        yml: str, optional
            A WindIO `yml` file containing the description of the farm
        coordFile: str, optional
            Wind Farm layout coordinates text file.
        WindTurbine: WindTurbine, optional
            WindTurbine object (only one type per WindFarm)
        """

        if (coordFile):
            coordArray = np.loadtxt(coordFile)
            self.pos = coordArray.T  # np.array(2 x nWT)
            self.pos = coordArray  # np.array(2 x nWT)
            self.nWT = self.pos.shape[1]
            self.WT = WindTurbineList([WT for i in range(self.nWT)])
            if name:
                self.name = name
            else:
                self.name = 'Unknown wind farm'

        elif (yml and array is not None):
            self.wf = WTLayout(yml)
            #self.wf = yml
            self.pos = array  # np.array(2 x nWT)
            self.nWT = self.pos.shape[1]
            self.WT = WindTurbineList([WindTurbineDICT(wt, self.wf[wt['turbine_type']]) for wt in self.wf.wt_list])
            self.name = self.wf.name

        elif (yml):
            self.wf = WTLayout(yml)
            self.pos = self.wf.positions.T
            self.nWT = self.pos.shape[1]
            self.WT = WindTurbineList([WindTurbineDICT(wt, self.wf[wt['turbine_type']]) for wt in self.wf.wt_list])
            self.name = self.wf.name
        elif (array.any()):
            coordArray = array
            self.pos = coordArray  # np.array(2 x nWT)
            self.nWT = self.pos.shape[1]
            self.WT = WindTurbineList([WT for i in range(self.nWT)])


        # We generate a wind turbine list

        # XYZ position of the rotors
        #self.H = np.ones(self.nWT)*self.H[0]
        self.xyz = np.vstack([self.pos, self.H])

        # Vector from iWT to jWT: self.vectWTtoWT[:,i,j] [3, nWT, nWT]
        self.vectWTtoWT = np.swapaxes([self.xyz -
            np.repeat(np.atleast_2d(self.xyz[:, i]).T, self.nWT, axis=1)
            for i in range(self.nWT)], 0, 1)


    def rep_str(self):
        return "%s has %s %s wind turbines, with a total capacity of %4.1f MW"%(
            self.name, self.nWT, self.WT.turbine_type, sum(self.rated_power)/1E3)

    def __repr__(self):
        sep = "-------------------------------------------------------------"
        return '\n'.join([sep, self.rep_str(), sep])

    def _repr_html_(self):
        sep = "<br>"
        return '\n'.join([sep, self.rep_str(), sep])

    def turbineDistance(self, wd):
        """Computes the WT to WT distance in flow coordinates
        ranks the most of most upstream turbines

        Parameters
        ----------
        wd: float
            Wind direction in degrees

        Returns
        -------
        distFlowCoord: Vector from iWT to jWT: self.vectWTtoWT[:,i,j]
        idWT: ndarray(int)
            turbine index array
        """
        angle = np.radians(270.-wd)
        ROT = np.array([[np.cos(angle), np.sin(angle)],
                        [-np.sin(angle), np.cos(angle)]])
        distFlowCoord = np.einsum('ij,jkl->ikl', ROT, self.vectWTtoWT[:2, :, :])
        nDownstream = [(distFlowCoord[0, i, :] < 0).sum() for i in range(self.nWT)]
        ID0 = np.argsort(nDownstream)
        return distFlowCoord, nDownstream, ID0


    def toFlowCoord(self, wd, vect):
        """Rotates a 2xN np.array to flow coordinates

        Parameters
        ----------
        wd: float
            Wind direction in degrees
        vect: ndarray
            Vector or Matrix 2xN

        Returns
        -------
        vect: ndarray
            Vector or Matrix 2xN
        """
        angle = np.radians(270.-wd)
        ROT = np.array([[np.cos(angle), np.sin(angle)],
                        [-np.sin(angle), np.cos(angle)]])

        return np.dot(ROT, vect)


    def get_T2T_gl_coord(self):
        """
        Function to calculated the turbine to turbine distances in the global
        coordinate system. (slower than version 2).

        Parameters
        ----------
        wt_layout   GenericWindFarmTurbineLayout (FusedWind)

        Returns
        -------
        x_g     x component of distance between Tj and Ti := x_g[i,j]
        y_g     y component of distance between Tj and Ti := y_g[i,j]
        z_g     z component of distance between Tj and Ti := z_g[i,j]

        """
        # Compute the turbine to turbine vector in global coordinates
        x_g = np.zeros([self.nWT, self.nWT])
        y_g = np.zeros([self.nWT, self.nWT])
        z_g = np.zeros([self.nWT, self.nWT])
        for i in range(self.nWT):
            for j in range(self.nWT):
                x_g[i,j] = self.xyz[0,j] - self.xyz[0,i]
                y_g[i,j] = self.xyz[1,j] - self.xyz[1,i]
                z_g[i,j] = self.xyz[2,j] - self.xyz[2,i]

        return x_g,y_g,z_g

    def get_T2T_gl_coord2(self):
        """
        Function to calculated the turbine to turbine distances in the global
        coordinate system. (faster).

        Parameters
        ----------
        wt_layout   GenericWindFarmTurbineLayout (FusedWind)

        Returns
        -------
        x_g     x component of distance between Tj and Ti := x_g[i,j]
        y_g     y component of distance between Tj and Ti := y_g[i,j]
        z_g     z component of distance between Tj and Ti := z_g[i,j]

        """
        x_g, y_g, z_g = self.vectWTtoWT
        #print x_g[0,1]
        return x_g, y_g, z_g


    def plot(self, WT_num=False):
        """ # TODO
        """
        if MATPLOTLIB:
            x = (self.pos[0, :] - min(self.pos[0, :])) / (2. * self.WT.R)
            y = (self.pos[1, :] - min(self.pos[1, :])) / (2. * self.WT.R)
            fig, ax = plt.subplots()
            ax.scatter(x, y, c='black')
            if WT_num:
                for i in range(0, self.nWT):
                    ax.annotate(i, (x[i], y[i]))
            elif not WT_num:
                print('No annotation of turbines')
            ax.set_xlabel('x/D [-]')
            ax.set_ylabel('y/D [-]')
            ax.axis('equal')
            ax.set_title(self.name)
            return fig, ax

    def plot_order(self, wd):
        """ # TODO
        """
        if MATPLOTLIB:
            x = (self.pos[0, :] - min(self.pos[0, :])) / 1000
            y = (self.pos[1, :] - min(self.pos[1, :])) / 1000
            dist, nDownstream, idWT = self.turbineDistance(wd)
            fig, ax = plt.subplots()
            ax.scatter(x, y, c='black')
            for i in range(0, self.nWT):
                ax.annotate(int(idWT[i]), (x[i], y[i]))
            ax.set_xlabel('x [km]')
            ax.set_ylabel('y [km]')
            ax.set_title(self.name+' Wind direction '+str(wd))
            return fig, ax

    def __getattr__(self, key):
        """Give access to a list of the properties of the turbine

        Parameters
        ----------
        key: str
            The parameter to return

        Returns
        -------
        parameters: list
            The parameter list of the turbines

        Example
        -------
            > wf = WindFarm(name='farm_name', yml=filename)
            > wf.rotor_diameter

            [80.0, 80.0, 80.0, 80.0, 80.0, ..., 80.0]
        """
        # Detect the edge case if key is 'WT'
        if not key in ['WT', 'nWT']:
            return [getattr(wt, key) for wt in self.WT]
