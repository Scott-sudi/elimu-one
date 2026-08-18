// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use

import 'dart:html' as html;
import 'dart:ui_web' as ui_web;

import 'package:flutter/widgets.dart';

Widget buildPdfFrame(String url) {
  final viewType = 'kalunga-pdf-${url.hashCode}';
  ui_web.platformViewRegistry.registerViewFactory(viewType, (int viewId) {
    final element = html.IFrameElement()
      ..src = url
      ..style.border = 'none'
      ..style.width = '100%'
      ..style.height = '100%';
    return element;
  });
  return HtmlElementView(viewType: viewType);
}
