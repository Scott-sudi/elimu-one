import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../config/api_config.dart';
import '../../constants/api_endpoints.dart';

/// Clés de stockage sécurisé des jetons JWT.
abstract final class TokenStorageKeys {
  static const access = 'kalunga_jwt_access';
  static const refresh = 'kalunga_jwt_refresh';
}

/// Intercepteur Dio : Authorization Bearer + refresh automatique sur 401.
class AuthInterceptor extends Interceptor {
  AuthInterceptor({
    required this.storage,
    required this.dio,
    this.onSessionExpired,
  });

  final FlutterSecureStorage storage;
  final Dio dio;
  final void Function()? onSessionExpired;

  bool _refreshing = false;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final skipAuth = options.extra['skipAuth'] == true;
    if (!skipAuth) {
      final access = await storage.read(key: TokenStorageKeys.access);
      if (access != null && access.isNotEmpty) {
        options.headers['Authorization'] = 'Bearer $access';
      }
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode != 401) {
      return handler.next(err);
    }

    final requestOptions = err.requestOptions;
    if (requestOptions.extra['skipAuth'] == true ||
        requestOptions.extra['retried'] == true) {
      onSessionExpired?.call();
      return handler.next(err);
    }

    final refreshed = await _tryRefresh();
    if (!refreshed) {
      onSessionExpired?.call();
      return handler.next(err);
    }

    final access = await storage.read(key: TokenStorageKeys.access);
    final opts = requestOptions.copyWith(
      headers: {
        ...requestOptions.headers,
        'Authorization': 'Bearer $access',
      },
      extra: {
        ...requestOptions.extra,
        'retried': true,
      },
    );

    try {
      final response = await dio.fetch(opts);
      handler.resolve(response);
    } on DioException catch (e) {
      handler.next(e);
    }
  }

  Future<bool> _tryRefresh() async {
    if (_refreshing) return false;
    _refreshing = true;
    try {
      final refresh = await storage.read(key: TokenStorageKeys.refresh);
      if (refresh == null || refresh.isEmpty) return false;

      final response = await Dio(
        BaseOptions(
          baseUrl: ApiConfig.baseUrl,
          headers: ApiConfig.defaultHeaders,
          connectTimeout: ApiConfig.connectTimeout,
          receiveTimeout: ApiConfig.receiveTimeout,
        ),
      ).post(
        ApiEndpoints.tokenRefresh,
        data: {'refresh': refresh},
        options: Options(extra: {'skipAuth': true}),
      );

      final body = response.data;
      if (body is! Map<String, dynamic>) return false;
      if (body['success'] != true) return false;

      final data = body['data'];
      if (data is! Map) return false;

      final newAccess = data['access']?.toString();
      final newRefresh = data['refresh']?.toString();
      if (newAccess == null || newAccess.isEmpty) return false;

      await storage.write(key: TokenStorageKeys.access, value: newAccess);
      if (newRefresh != null && newRefresh.isNotEmpty) {
        await storage.write(key: TokenStorageKeys.refresh, value: newRefresh);
      }
      return true;
    } catch (_) {
      await storage.delete(key: TokenStorageKeys.access);
      await storage.delete(key: TokenStorageKeys.refresh);
      return false;
    } finally {
      _refreshing = false;
    }
  }
}
