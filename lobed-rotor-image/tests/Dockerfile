# Verifier image (separate from the agent): FreeCAD + the freecad validator,
# with the held-back reference.FCStd baked at /opt/grader and the scorer/driver
# at /tests. Never shipped to the agent.
FROM condaforge/miniforge3@sha256:7de9956cd783d48955835e61b8d212c26b2df901d5a5be8217bd58fb6c1bd5a4

# `ocp` is the OCCT binding the validator's v2 geometry scorer imports. It comes
# from conda rather than the validator's `v2` extra so that OCP and FreeCAD link
# against the same VTK: the pip wheel pins vtk==9.6.2, pip cannot uninstall the
# conda-owned vtk to reach it, and conda cannot place vtk 9.6.2 beside
# freecad 1.1.0 on python 3.12 (libboost conflict). OCP loads
# libvtkWrappingPythonCore at import, so the two must agree.
RUN mamba install -n base -y -c conda-forge \
        python=3.12 "freecad=1.1.0" "numpy=2.4.6" "ocp=7.9.3.1" scipy pydantic \
 && mamba clean -afy

RUN echo /opt/conda/lib > "$(python -c 'import site; print(site.getsitepackages()[0])')/freecad.pth" \
 && python -c "import FreeCAD, numpy, pydantic, scipy; assert FreeCAD.Version()[:3] == ['1', '1', '0'], FreeCAD.Version(); assert numpy.__version__ == '2.4.6', numpy.__version__; print('runtime ok: FreeCAD', '.'.join(FreeCAD.Version()[:3]), 'numpy', numpy.__version__)" \
 && freecadcmd --version \
 && ! command -v ccx

RUN userdel -r ubuntu 2>/dev/null || true

WORKDIR /app
COPY LICENSES/ /app/LICENSES/

ENV FREECAD_LIB=/opt/conda/lib:/opt/conda/Mod:/opt/conda/share/Mod

# OpenGL + X11 libs for PyVista's headless renderer (answer.png snapshot).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libgl1 libxrender1 libxext6 libsm6 libice6 xvfb xauth \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Installed without the `v2` extra: conda already supplies OCP above, and the
# extra would pull the pip wheel and its conflicting vtk pin. `render` still
# comes from the extra. The import check proves the v2 backend loads.
ARG FREECAD_VALIDATOR_VERSION=0.6.0
ARG PYVISTA_VERSION=0.48.4
RUN python -m pip install --no-cache-dir \
        "gnucleus-freecad-validator[render]==${FREECAD_VALIDATOR_VERSION}" \
        "pyvista==${PYVISTA_VERSION}" \
 && python -c "from importlib.metadata import version; import FreeCAD, freecad_validator, pyvista; from OCP.BRepBndLib import BRepBndLib; from freecad_validator import Validator; validator_version = version('gnucleus-freecad-validator'); assert FreeCAD.Version()[:3] == ['1', '1', '0'], FreeCAD.Version(); assert validator_version == '${FREECAD_VALIDATOR_VERSION}', validator_version; assert pyvista.__version__ == '${PYVISTA_VERSION}', pyvista.__version__; assert callable(BRepBndLib.AddOBB_s); Validator(scorer_version='v2'); print('verifier runtime ok:', FreeCAD.Version()[:3], validator_version, pyvista.__version__, 'v2 scorer ok')"

ENV PYVISTA_OFF_SCREEN=true

COPY grader/ /opt/grader/
COPY . /tests/
