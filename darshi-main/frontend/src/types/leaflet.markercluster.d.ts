/**
 * Type declarations for leaflet.markercluster
 * This file provides TypeScript support for the leaflet.markercluster library
 */

declare module 'leaflet.markercluster' {
  import * as L from 'leaflet';

  // Extend Leaflet namespace with MarkerClusterGroup
  namespace L {
    class MarkerClusterGroup extends L.FeatureGroup {
      constructor(options?: MarkerClusterGroupOptions);
      addLayer(layer: L.Layer): this;
      removeLayer(layer: L.Layer): this;
      clearLayers(): this;
    }

    interface MarkerClusterGroupOptions {
      showCoverageOnHover?: boolean;
      zoomToBoundsOnClick?: boolean;
      spiderfyOnMaxZoom?: boolean;
      removeOutsideVisibleBounds?: boolean;
      animate?: boolean;
      animateAddingMarkers?: boolean;
      disableClusteringAtZoom?: number;
      maxClusterRadius?: number | ((zoom: number) => number);
      polygonOptions?: L.PolylineOptions;
      singleMarkerMode?: boolean;
      spiderLegPolylineOptions?: L.PolylineOptions;
      spiderfyDistanceMultiplier?: number;
      iconCreateFunction?: (cluster: any) => L.Icon | L.DivIcon;
      chunkedLoading?: boolean;
      chunkInterval?: number;
      chunkDelay?: number;
      chunkProgress?: (processed: number, total: number, elapsed: number) => void;
    }

    function markerClusterGroup(options?: MarkerClusterGroupOptions): MarkerClusterGroup;
  }

  export = L;
}

declare module 'leaflet.markercluster/dist/MarkerCluster.css';
declare module 'leaflet.markercluster/dist/MarkerCluster.Default.css';
